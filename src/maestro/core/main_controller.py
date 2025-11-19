import os
import datetime
import json
import ast
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
    #  CORE 2: SWE-bench Workflow (Group E -> D 통합/연계)
    # ====================================================
    def run_swe_workflow(self, output_base_dir: str, limit: int = 1):
        """SWE-bench 벤치마크 실행 로직 (E-D 연계형)"""
        print(f"\n===== [SWE-bench] 워크플로우 시작 (Limit: {limit}) =====")
        try:
            dataset = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
        except NameError:
            print("오류: 'datasets' 라이브러리가 설치되지 않았습니다.")
            return

        count = 0
        for instance in dataset:
            if count >= limit: break
            
            instance_id = instance['instance_id']
            print(f"\n>>> Processing Issue: {instance_id}")
            
            # 컨텍스트 준비
            context = f"Repository: {instance['repo']}\nIssue:\n{instance['problem_statement']}"
            
            # -------------------------------------------------------
            # 1. Group B (Simple LLM) - 독립 실행
            # -------------------------------------------------------
            self._run_group_b(instance, context, output_base_dir)

            # -------------------------------------------------------
            # 2. Group C (Rule-Based) - 독립 실행
            # -------------------------------------------------------
            self._run_group_c(instance, context, output_base_dir)

            # -------------------------------------------------------
            # 3. Group E & D (MAESTRO Standard & Retro) - 통합 실행
            # -------------------------------------------------------
            # 이 로직은 E(1차 시도)를 먼저 수행하고, 그 결과를 바탕으로 D(회고)를 수행합니다.
            self._run_group_e_and_d_combined(instance, context, output_base_dir)
            
            count += 1

    def _run_group_b(self, instance, context, base_dir):
        """Group B: 단순 LLM 실행"""
        task_dir = os.path.join(base_dir, instance['instance_id'], "B")
        os.makedirs(task_dir, exist_ok=True)
        print(f"   [B] 실행 중... (Simple Mode)")
        
        # B는 전문가/아키텍트 없이 바로 개발자에게 던지거나 단순화된 아키텍트 사용
        plan = self.architect_agent.run(context, [], "N/A", synthesis_goal="Resolve Issue", architect_mode="CoT")
        if plan:
            dev_out = self.developer_agent.run(context, plan)
            if dev_out and dev_out.status == "SUCCESS":
                write_text_file(os.path.join(task_dir, "final_code.py"), dev_out.final_code)
                print(f"   [B] 성공: 저장됨")

    def _run_group_c(self, instance, context, base_dir):
        """Group C: 규칙 기반 아키텍트"""
        task_dir = os.path.join(base_dir, instance['instance_id'], "C")
        os.makedirs(task_dir, exist_ok=True)
        print(f"   [C] 실행 중... (RuleBased Mode)")

        # 전문가 분석
        perf = self.performance_expert.run(context, "N/A")
        read = self.readability_expert.run(context, "N/A")
        sec = self.security_expert.run(context, "N/A")
        all_reports = (perf or []) + (read or []) + (sec or [])

        # 규칙 기반 아키텍트
        plan = self.architect_agent.run(context, all_reports, "N/A", synthesis_goal="Resolve Issue", architect_mode="RuleBased")
        
        if plan:
            dev_out = self.developer_agent.run(context, plan)
            if dev_out and dev_out.status == "SUCCESS":
                write_text_file(os.path.join(task_dir, "final_code.py"), dev_out.final_code)
                print(f"   [C] 성공: 저장됨")
            else:
                print(f"   [C] 실패: 개발자 오류")

    def _run_group_e_and_d_combined(self, instance, context, base_dir):
        """
        Group E(1차) -> Quality Gate -> Group D(회고)로 이어지는 정교한 파이프라인
        """
        e_dir = os.path.join(base_dir, instance['instance_id'], "E")
        d_dir = os.path.join(base_dir, instance['instance_id'], "D")
        os.makedirs(e_dir, exist_ok=True)
        os.makedirs(d_dir, exist_ok=True)

        print(f"   [E & D] 통합 실행 시작...")

        # 1. 전문가 자문 (공통)
        perf = self.performance_expert.run(context, "N/A")
        read = self.readability_expert.run(context, "N/A")
        sec = self.security_expert.run(context, "N/A")
        all_reports = (perf or []) + (read or []) + (sec or [])

        # 2. 1차 시도 (Group E 결과)
        print(f"   [E] 1차 시도 (Architect & Developer)...")
        plan_v1 = self.architect_agent.run(context, all_reports, "N/A", synthesis_goal="Resolve Issue", architect_mode="CoT")
        
        if not plan_v1:
            print(f"   [E/D] 실패: 1차 계획 수립 불가")
            return

        dev_out_v1 = self.developer_agent.run(context, plan_v1)
        if not dev_out_v1 or dev_out_v1.status != "SUCCESS":
            print(f"   [E] 실패: 1차 구현 실패")
            return

        # 저장
        write_text_file(os.path.join(e_dir, "final_code.py"), dev_out_v1.final_code)
        write_text_file(os.path.join(d_dir, "final_code.py"), dev_out_v1.final_code)
        print(f"   [E] 완료: 1차 결과 저장됨.")

        # -------------------------------------------------------
        # 3. Quality Gate & Smart Feedback (Blind Retrospection 해결)
        # -------------------------------------------------------
        print(f"   [D] 1차 결과 정밀 검사 중...")
        
        # (1) 문법 및 정적 분석 실행
        qg_result = self._run_quality_gate("N/A", dev_out_v1.final_code)
        
        # (2) 피드백 생성 로직
        failure_feedback = ""
        is_syntax_error = False

        # Case A: 문법 오류 발생 (가장 치명적)
        if qg_result.get("details", {}).get("error") == "SyntaxError":
            error_msg = qg_result["details"]["message"]
            print(f"   [D] 🚨 문법 오류 감지! ({error_msg})")
            failure_feedback = f"CRITICAL SYNTAX ERROR in previous attempt: {error_msg}. You MUST fix this syntax error immediately."
            is_syntax_error = True
            
        # Case B: 문법은 통과했으나, 시뮬레이션 테스트 실패 (나중에 Docker 결과로 대체될 부분)
        elif not is_syntax_error:
            print(f"   [D] 문법 통과. 기능 테스트(Simulation) 진행...")
            # TODO: 추후 실제 Docker 실행 결과(stderr)를 여기에 넣어야 함.
            # 현재는 가상의 ImportError 상황을 부여하여 'Path Hallucination'을 점검하게 유도함.
            failure_feedback = (
                "TEST FAILURE: ImportError: cannot import name '...' from partially initialized module. "
                "It seems you might be importing a non-existent file or creating a circular dependency. "
                "Check file paths and imports."
            )

        # 4. 자기 회고 루프 진입
        print(f"   [D] ⚠️ 회고 시작. 피드백: {failure_feedback[:100]}...")

        plan_v2 = self.architect_agent.run(
            context, all_reports, "N/A", 
            synthesis_goal="Resolve Issue", 
            failure_feedback=failure_feedback # <--- 구체적인 에러 메시지 전달
        )

        if not plan_v2:
            print(f"   [D] 회고 실패: 수정 계획 수립 불가")
            return

        dev_out_v2 = self.developer_agent.run(context, plan_v2)

        if dev_out_v2 and dev_out_v2.status == "SUCCESS":
            write_text_file(os.path.join(d_dir, "final_code.py"), dev_out_v2.final_code)
            print(f"   [D] ✅ 회고 후 수정 완료! (Smart Feedback 적용됨)")
        else:
            print(f"   [D] 회고 실패: 수정 구현 실패")

    # ====================================================
    #  SHARED: Helper Methods
    # ====================================================
    def _run_quality_gate(
        self, original_code: str, modified_code: str
    ) -> Dict[str, Any]:
        """
        수정된 코드의 품질을 측정합니다.
        [개선됨] 0단계: Syntax Check (문법 검사)를 통과 못 하면 즉시 0점 처리하고 종료합니다.
        """
        print("\n--- 품질 게이트 실행 ---")
        
        scores = {"security": 0, "readability": 0, "performance": 0}
        
        # -------------------------------------------------------
        # [0단계] Syntax Pre-check (문지기)
        # -------------------------------------------------------
        print("0단계: Python 문법 유효성 검사 (Syntax Check)...")
        try:
            ast.parse(modified_code)
            print(">> 문법 검사 통과 (Valid Python Code)")
        except SyntaxError as e:
            error_msg = f"SyntaxError: {e.msg} (Line {e.lineno})"
            print(f"🚨 [치명적 오류] 문법 검사 실패: {error_msg}")
            print(">> 분석을 중단하고 0점을 부여합니다.")
            
            return {
                "total_score": 0,
                "scores": scores,
                "details": {
                    "error": "SyntaxError",
                    "message": error_msg
                },
            }
        except Exception as e:
            print(f"🚨 [오류] 문법 검사 중 알 수 없는 오류: {e}")
            return {"total_score": 0, "scores": scores, "details": {"error": str(e)}}

        # -------------------------------------------------------
        # [1~3단계] 기존 정적/동적 분석 (문법 통과 시에만 실행)
        # -------------------------------------------------------
        
        # 분석 보고서 초기화
        sec_report = analyze_security(modified_code)
        read_report = None
        perf_report = None

        # 1. 가독성 분석
        print("1단계: 가독성 분석 시작 (순환 복잡도)...")
        try:
            read_report = analyze_readability(modified_code)
            if read_report and read_report.success:
                complexity = read_report.average_complexity
                if 1 <= complexity <= 10: scores["readability"] = 30
                elif 11 <= complexity <= 20: scores["readability"] = 15
        except Exception as e:
            print(f"가독성 분석 중 오류(무시됨): {e}")
            scores["readability"] = 0
        
        # 2. 성능 분석
        print("2단계: 성능 분석 시작 (실행 시간 측정)...")
        try:
            perf_report = profile_performance(original_code, modified_code)
            if perf_report and perf_report.success:
                improvement = perf_report.improvement_percentage
                if improvement >= 15: scores["performance"] = 30
                elif 5 <= improvement < 15: scores["performance"] = 15
                elif 0 <= improvement < 5: scores["performance"] = 5
        except Exception as e:
            print(f"성능 분석 중 오류(무시됨): {e}")
            scores["performance"] = 0

        # 3. 보안 점수 계산
        if sec_report.success:
            if sec_report.highest_severity == "HIGH": scores["security"] = 0
            elif sec_report.highest_severity == "MEDIUM": scores["security"] = 15
            elif sec_report.highest_severity == "LOW": scores["security"] = 30
            else: scores["security"] = 40

        total_score = sum(scores.values())
        print(f"품질 게이트 결과: 총점 = {total_score}/100")

        return {
            "total_score": total_score,
            "scores": scores,
            "details": {
                "security": sec_report,
                "readability": read_report, 
                "performance": perf_report,
            },
        }

    def _save_results(self, output_dir, final_code, report):
        """결과 파일 저장"""
        os.makedirs(output_dir, exist_ok=True)
        write_text_file(os.path.join(output_dir, "final_code.py"), final_code)
        with open(os.path.join(output_dir, "final_report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)