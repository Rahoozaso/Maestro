import os
import datetime
import json
from typing import Dict, Any, Optional

# --- 외부 라이브러리 (SWE-bench용) ---
try:
    from datasets import load_dataset
    import docker
except ImportError:
    pass # HumanEval만 돌릴 때는 없어도 됨

# --- 유틸리티 및 설정 ---
from maestro.utils.file_io import read_text_file, write_text_file
from maestro.utils.llm_handler import set_llm_provider

# --- 에이전트 ---
from maestro.agents.expert_agents import (
    PerformanceExpert,
    ReadabilityExpert,
    SecurityExpert,
)
from maestro.agents.architect_agent import ArchitectAgent
from maestro.agents.developer_agent import DeveloperAgent

# --- 분석 도구 (HumanEval용) ---
from maestro.tools.performance_profiler import profile_performance
from maestro.tools.readability_analyzer import analyze_readability
from maestro.tools.security_analyzer import analyze_security


class MainController:
    """
    MAESTRO 프레임워크의 전체 워크플로우를 조율하는 통합 컨트롤러입니다.
    HumanEval(단일 파일)과 SWE-bench(리포지토리)를 모두 지원합니다.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        set_llm_provider(config["llm"])

        # 에이전트 인스턴스화 (공통 사용)
        self.performance_expert = PerformanceExpert(config)
        self.readability_expert = ReadabilityExpert(config)
        self.security_expert = SecurityExpert(config)
        self.architect_agent = ArchitectAgent(config)
        self.developer_agent = DeveloperAgent(config)

        print("MainController(Integrated) 초기화 완료.")

    # ====================================================
    #  CORE 1: HumanEval Workflow (기존 로직 유지)
    # ====================================================
    def run_humaneval_workflow(
        self,
        source_code_path: str,
        unit_test_path: str,
        output_dir: str,
        architect_mode: str = "CoT",
        enable_retrospection: bool = True,
    ):
        """HumanEval 벤치마크 실행 로직"""
        run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"\n===== [HumanEval] 워크플로우 시작 (Run ID: {run_id}) =====")

        try:
            v_gen = read_text_file(source_code_path)
            unit_tests = read_text_file(unit_test_path)
        except FileNotFoundError:
            return

        # 1. 전문가 자문
        print("\n--- 1단계: 전문가 자문 ---")
        perf_reports = self.performance_expert.run(v_gen, unit_tests)
        read_reports = self.readability_expert.run(v_gen, unit_tests)
        sec_reports = self.security_expert.run(v_gen, unit_tests)
        all_reports = (perf_reports or []) + (read_reports or []) + (sec_reports or [])

        # 제안 없음 처리 (Pass-through)
        if not all_reports:
            print("모든 전문가가 개선안을 제시하지 않았습니다. 원본 유지 및 종료.")
            quality_result = self._run_quality_gate(v_gen, v_gen)
            final_report = {
                "run_id": run_id,
                "status": "NO_CHANGES_NEEDED",
                "initial_attempt": {"quality": quality_result, "developer_log": ["No suggestions."]}
            }
            self._save_results(output_dir, v_gen, final_report)
            return

        print(f"총 {len(all_reports)}개의 개선안 수집 완료.")

        # 2. 아키텍트
        print("\n--- 2단계: 아키텍트 의사결정 ---")
        plan = self.architect_agent.run(v_gen, all_reports, unit_tests, architect_mode=architect_mode)
        if not plan:
            print("아키텍트가 실행 계획 생성 실패. 종료.")
            return

        # 3. 개발자
        print("\n--- 3단계: 개발자 구현 ---")
        dev_output = self.developer_agent.run(v_gen, plan)
        if not dev_output or dev_output.status == "FAILURE":
            print("개발자 에이전트 실패. 종료.")
            return
        v_final = dev_output.final_code

        # 4. 품질 검증 및 회고
        quality_result = self._run_quality_gate(v_gen, v_final)
        final_report = {
            "run_id": run_id,
            "initial_attempt": {"quality": quality_result, "developer_log": dev_output.log},
        }

        if (quality_result["total_score"] >= 85 and quality_result["scores"]["security"] > 0):
            print("\n 품질 기준 충족! 성공.")
            final_report["status"] = "SUCCESS_FIRST_TRY"
            self._save_results(output_dir, v_final, final_report)
            return
        elif not enable_retrospection:
            print("\n 품질 미달 (회고 비활성). 종료.")
            final_report["status"] = "FAILURE_NO_RETROSPECTION"
            self._save_results(output_dir, v_final, final_report)
            return

        # 4.5 회고 루프
        print("\n--- 4.5단계: 회고 루프 진입 ---")
        failure_feedback = f"1차 실패. 총점: {quality_result['total_score']}."
        
        if architect_mode == "RuleBased":
            final_report["status"] = "FINAL_FAILURE_RULEBASED"
            self._save_results(output_dir, v_final, final_report)
            return

        revised_plan = self.architect_agent.run(v_gen, all_reports, unit_tests, failure_feedback=failure_feedback)
        revised_dev_output = self.developer_agent.run(v_gen, revised_plan)
        
        if not revised_dev_output or revised_dev_output.status == "FAILURE":
            final_report["status"] = "FINAL_FAILURE"
            self._save_results(output_dir, v_final, final_report)
            return

        v_final_rev2 = revised_dev_output.final_code
        final_quality_result = self._run_quality_gate(v_gen, v_final_rev2)
        final_report["retrospection_attempt"] = {
            "quality": final_quality_result,
            "developer_log": revised_dev_output.log
        }
        
        status = "SUCCESS_AFTER_RETROSPECTION" if final_quality_result["total_score"] >= 85 else "FINAL_FAILURE"
        print(f"\n 최종 결과: {status}")
        final_report["status"] = status
        self._save_results(output_dir, v_final_rev2, final_report)


    # ====================================================
    #  CORE 2: SWE-bench Workflow (신규 통합)
    # ====================================================
    def run_swe_workflow(self, output_base_dir: str, limit: int = 1):
        """SWE-bench 벤치마크 실행 로직 (통합됨)"""
        print(f"\n===== [SWE-bench] 워크플로우 시작 (Limit: {limit}) =====")
        try:
            dataset = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
        except NameError:
            print("오류: 'datasets' 라이브러리가 설치되지 않았습니다. 'pip install datasets'를 실행하세요.")
            return

        count = 0
        for instance in dataset:
            if count >= limit: break
            
            instance_id = instance['instance_id']
            print(f"\n>>> Processing Issue: {instance_id}")
            
            # SWE-bench는 4개 그룹을 모두 순차 실행
            self._run_single_swe_instance(instance, output_base_dir, "B", "CoT", False)
            self._run_single_swe_instance(instance, output_base_dir, "C", "RuleBased", False)
            self._run_single_swe_instance(instance, output_base_dir, "E", "CoT", False)
            self._run_single_swe_instance(instance, output_base_dir, "D", "CoT", True) # Full Maestro
            
            count += 1

    def _run_single_swe_instance(self, instance, base_dir, group_name, mode, retro):
        """단일 SWE 이슈에 대한 특정 그룹 실행"""
        instance_id = instance['instance_id']
        task_dir = os.path.join(base_dir, instance_id, group_name)
        os.makedirs(task_dir, exist_ok=True)
        
        print(f"   [{group_name}] 실행 중... (Mode: {mode}, Retro: {retro})")
        
        # 컨텍스트 구성
        context = f"Repository: {instance['repo']}\nIssue:\n{instance['problem_statement']}"
        
        # 1. 전문가
        all_reports = []
        if group_name != "B": # B그룹은 전문가 단계 생략 (단일 프롬프트)
            perf = self.performance_expert.run(context, "N/A")
            read = self.readability_expert.run(context, "N/A")
            sec = self.security_expert.run(context, "N/A")
            all_reports = (perf or []) + (read or []) + (sec or [])

        # 2. 아키텍트 & 3. 개발자
        # (SWE-bench용 프롬프트가 적용된 에이전트를 그대로 재사용)
        if group_name == "B":
            # Group B는 아키텍트 없이 바로 개발자에게 "고쳐줘"라고 요청하는 구조 (단순화)
            # 여기서는 편의상 아키텍트를 통하되 아주 단순한 지시만 내리도록 하거나,
            # 별도의 simple_prompt 로직을 구현해야 합니다. (현재는 D와 동일하게 처리하되 report만 없음)
            plan = self.architect_agent.run(context, [], "N/A", synthesis_goal="Resolve Issue", architect_mode="CoT")
        else:
            plan = self.architect_agent.run(context, all_reports, "N/A", synthesis_goal="Resolve Issue", architect_mode=mode)
        
        if not plan:
            print(f"   [{group_name}] 실패: 계획 수립 불가")
            return

        dev_out = self.developer_agent.run(context, plan)
        
        if dev_out and dev_out.status == "SUCCESS":
            patch_path = os.path.join(task_dir, "patch.py")
            write_text_file(patch_path, dev_out.final_code)
            print(f"   [{group_name}] 성공: 패치 저장됨 -> {patch_path}")
            
            # TODO: 여기서 Docker를 사용하여 'patch.py'를 적용하고 채점하는 로직(Quality Gate)이 추가되어야 합니다.
            # 현재는 패치 생성까지만 수행합니다.
        else:
            print(f"   [{group_name}] 실패: 구현 실패")

    # ====================================================
    #  SHARED: Helper Methods
    # ====================================================
    def _run_quality_gate(self, original_code, modified_code):
        """HumanEval용 품질 게이트 (Crash 방지 적용)"""
        # (이전에 드렸던 Robust 코드를 그대로 사용)
        print("\n--- 품질 게이트 실행 ---")
        sec_report = analyze_security(modified_code)
        scores = {"security": 0, "readability": 0, "performance": 0}

        try:
            read_report = analyze_readability(modified_code)
            if read_report and read_report.success:
                # 점수 계산 로직...
                pass 
        except Exception:
            pass # 0점 처리

        try:
            perf_report = profile_performance(original_code, modified_code)
            if perf_report and perf_report.success:
                # 점수 계산 로직...
                pass
        except Exception:
            pass

        # (점수 계산 생략 - 기존 코드 유지)
        return {"total_score": 0, "scores": scores, "details": {}}

    def _save_results(self, output_dir, final_code, report):
        """결과 파일 저장"""
        os.makedirs(output_dir, exist_ok=True)
        write_text_file(os.path.join(output_dir, "final_code.py"), final_code)
        with open(os.path.join(output_dir, "final_report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)