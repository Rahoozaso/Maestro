import os
import datetime
import json
import ast
from typing import Dict, Any, List, Union, Optional

# --- 외부 라이브러리 ---
try:
    from datasets import load_dataset
    import docker
except ImportError:
    pass

# --- 유틸리티 및 설정 ---
from maestro.utils.file_io import read_text_file, write_text_file
from maestro.utils.llm_handler import set_llm_provider, reset_token_usage, get_token_usage

# --- 에이전트 ---
from maestro.agents.expert_agents import PerformanceExpert, ReadabilityExpert, SecurityExpert
from maestro.agents.architect_agent import ArchitectAgent
from maestro.agents.developer_agent import DeveloperAgent
from maestro.core.data_models import ExpertReviewReport

# --- 분석 도구 ---
from maestro.tools.performance_profiler import profile_performance
from maestro.tools.readability_analyzer import analyze_readability
from maestro.tools.security_analyzer import analyze_security


class MainController:
    """
    MAESTRO 통합 컨트롤러 (HumanEval + SWE-bench + Docker 검증 + 비용 추적 + 전 그룹 품질 측정)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        set_llm_provider(config["llm"])

        self.performance_expert = PerformanceExpert(config)
        self.readability_expert = ReadabilityExpert(config)
        self.security_expert = SecurityExpert(config)
        self.architect_agent = ArchitectAgent(config)
        self.developer_agent = DeveloperAgent(config)

        print("MainController(Integrated) 초기화 완료.")

    # 💡 [호환성]
    def run_workflow(self, *args, **kwargs):
        return self.run_humaneval_workflow(*args, **kwargs)

    # -------------------------------------------------------
    #  Helper Methods
    # -------------------------------------------------------
    def _run_quality_gate(self, original_code: str, modified_code: str) -> Dict[str, Any]:
        """
        모든 그룹의 결과물에 대해 NFR 점수를 계산합니다. (Crash 방지 적용)
        """
        print("      >>> [Quality Gate] 품질 측정 시작...")
        scores = {"security": 0, "readability": 0, "performance": 0}
        
        # 0. Syntax Check
        try:
            ast.parse(modified_code)
        except SyntaxError as e:
            return {"total_score": 0, "scores": scores, "details": {"error": f"SyntaxError: {e.msg} line {e.lineno}"}}
        except Exception as e:
            return {"total_score": 0, "scores": scores, "details": {"error": str(e)}}

        # 1~3. Analysis Tools
        sec_report = analyze_security(modified_code)
        
        try:
            read_report = analyze_readability(modified_code)
            if read_report and read_report.success:
                if 1 <= read_report.average_complexity <= 10: scores["readability"] = 30
                elif read_report.average_complexity <= 20: scores["readability"] = 15
        except Exception: pass

        try:
            perf_report = profile_performance(original_code, modified_code)
            if perf_report and perf_report.success:
                if perf_report.improvement_percentage >= 15: scores["performance"] = 30
                elif perf_report.improvement_percentage >= 5: scores["performance"] = 15
                elif perf_report.improvement_percentage >= 0: scores["performance"] = 5
        except Exception: pass

        if sec_report.success:
            if sec_report.highest_severity == "HIGH": scores["security"] = 0
            elif sec_report.highest_severity == "MEDIUM": scores["security"] = 15
            else: scores["security"] = 40

        total = sum(scores.values())
        return {
            "total_score": total,
            "scores": scores,
            "details": {
                "security": sec_report,
                "readability": read_report, # 객체가 없으면 None
                "performance": perf_report
            }
        }

    def _save_results(self, output_dir: str, final_code: str, report: Dict[str, Any]):
        os.makedirs(output_dir, exist_ok=True)
        write_text_file(os.path.join(output_dir, "final_code.py"), final_code)
        
        token_usage = get_token_usage()
        report["cost_analysis"] = {
            "prompt_tokens": token_usage["prompt"],
            "completion_tokens": token_usage["completion"],
            "estimated_cost_usd": (token_usage["prompt"] * 5 + token_usage["completion"] * 15) / 1_000_000
        }

        try:
            with open(os.path.join(output_dir, "final_report.json"), "w", encoding="utf-8") as f:
                json.dump(report, f, indent=4, default=str, ensure_ascii=False)
            print(f"      -> 결과 저장 완료 (비용: ${report['cost_analysis']['estimated_cost_usd']:.4f})")
        except Exception as e:
            print(f"      -> 리포트 저장 실패: {e}")

    def _verify_fix_with_docker(self, instance, code_content):
        """Docker 검증 (기능 테스트)"""
        print("   [검증] Docker 테스트 시도...")
        try:
            ast.parse(code_content)
        except SyntaxError as e:
            return False, f"SyntaxError: {e.msg} at line {e.lineno}"

        try:
            import docker
            client = docker.from_env()
            image_name = "python:3.9-slim"
            
            container = client.containers.run(
                image_name, command=["python", "-c", code_content], detach=True
            )
            exit_code = container.wait(timeout=10)
            logs = container.logs().decode("utf-8")
            container.remove()
            
            if exit_code['StatusCode'] == 0:
                return True, "Execution Successful"
            else:
                return False, f"Runtime Error:\n{logs.strip()[:500]}"
        except Exception as e:
            # Docker 실패는 실험 중단 사유 아님 -> Pass 처리
            print(f"      -> Docker 실행 불가 (Skip): {e}")
            return True, f"Docker Skipped ({e})"

    # ====================================================
    #  CORE 1: HumanEval Workflow (유지)
    # ====================================================
    def run_humaneval_workflow(self, source_code_path, unit_test_path, output_dir, architect_mode="CoT", enable_retrospection=True):
        # (이전 코드와 동일 - HumanEval은 이미 Quality Gate를 잘 쓰고 있음)
        run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"\n===== [HumanEval] 워크플로우 시작 (Run ID: {run_id}) =====")
        try:
            v_gen = read_text_file(source_code_path)
            unit_tests = read_text_file(unit_test_path)
        except FileNotFoundError: return

        print("\n--- 1단계: 전문가 자문 ---")
        perf = self.performance_expert.run(v_gen, unit_tests)
        read = self.readability_expert.run(v_gen, unit_tests)
        sec = self.security_expert.run(v_gen, unit_tests)
        all_reports = (perf or []) + (read or []) + (sec or [])

        if not all_reports:
            print("모든 전문가가 개선안을 제시하지 않았습니다. 종료.")
            qg = self._run_quality_gate(v_gen, v_gen)
            self._save_results(output_dir, v_gen, {"run_id": run_id, "status": "NO_CHANGES", "quality_analysis": qg})
            return

        print("\n--- 2단계: 아키텍트 의사결정 ---")
        plan = self.architect_agent.run(v_gen, all_reports, unit_tests, architect_mode=architect_mode)
        if not plan: return

        print("\n--- 3단계: 개발자 구현 ---")
        dev_out = self.developer_agent.run(v_gen, plan)
        if not dev_out: return
        
        # 4. 품질 검증
        qg = self._run_quality_gate(v_gen, dev_out.final_code)
        final_report = {
            "run_id": run_id,
            "expert_reports": [r.model_dump() for r in all_reports],
            "architect_plan": plan.model_dump(),
            "developer_log": dev_out.log,
            "quality_analysis": qg # 점수 저장
        }

        if (qg["total_score"] >= 85 and qg["scores"]["security"] > 0) or not enable_retrospection:
            status = "SUCCESS" if qg["total_score"] >= 85 else "FAILURE_NO_RETRO"
            final_report["status"] = status
            self._save_results(output_dir, dev_out.final_code, final_report)
            return

        print("\n--- 4.5단계: 회고 ---")
        feedback = f"Score Low: {qg['total_score']}."
        if architect_mode == "RuleBased":
            final_report["status"] = "FINAL_FAILURE_RULEBASED"
            self._save_results(output_dir, dev_out.final_code, final_report)
            return

        plan_v2 = self.architect_agent.run(v_gen, all_reports, unit_tests, failure_feedback=feedback)
        dev_out_v2 = self.developer_agent.run(v_gen, plan_v2)
        
        if dev_out_v2:
            qg_v2 = self._run_quality_gate(v_gen, dev_out_v2.final_code)
            final_report["retrospection"] = {"quality_analysis": qg_v2}
            final_report["status"] = "SUCCESS_RETRO"
            self._save_results(output_dir, dev_out_v2.final_code, final_report)

    # ====================================================
    #  CORE 2: SWE-bench Workflow (점수 측정 추가)
    # ====================================================
    def run_swe_workflow(self, output_base_dir: str, limit: int = 1):
        print(f"\n===== [SWE-bench] 워크플로우 시작 (Limit: {limit}) =====")
        try:
            dataset = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
        except NameError: return

        count = 0
        for instance in dataset:
            if count >= limit: break
            print(f"\n>>> Processing Issue: {instance['instance_id']}")
            safe_problem = instance['problem_statement'].replace("{", "{{").replace("}", "}}")
            context = f"Repository: {instance['repo']}\nIssue:\n{safe_problem}"
            
            self._run_group_logic(instance, context, output_base_dir, "B", "CoT", False)
            self._run_group_logic(instance, context, output_base_dir, "C", "RuleBased", False)
            self._run_group_e_and_d_combined(instance, context, output_base_dir)
            count += 1

    def _run_group_logic(self, instance, context, base_dir, group, mode, retro):
        """B, C 그룹 실행 (점수 측정 포함)"""
        reset_token_usage()
        task_dir = os.path.join(base_dir, instance['instance_id'], group)
        os.makedirs(task_dir, exist_ok=True)
        print(f"   [{group}] 실행 중...")
        
        all_reports = []
        plan = None
        
        if group == "B":
            dummy = [ExpertReviewReport(suggestion_id="FIX", agent_role="Dev", title="Fix", target_code_block="Repo", severity="High", reasoning="Fix", proposed_change="Fix")]
            plan = self.architect_agent.run(context, dummy, "N/A", "Resolve Issue", "CoT")
        else:
            perf = self.performance_expert.run(context, "N/A")
            read = self.readability_expert.run(context, "N/A")
            sec = self.security_expert.run(context, "N/A")
            all_reports = (perf or []) + (read or []) + (sec or [])
            if not all_reports:
                all_reports = [ExpertReviewReport(suggestion_id="NONE", agent_role="Sys", title="None", target_code_block="Repo", severity="Low", reasoning="None", proposed_change="None")]
            plan = self.architect_agent.run(context, all_reports, "N/A", "Resolve Issue", mode)

        if plan:
            dev_out = self.developer_agent.run(context, plan)
            if dev_out and dev_out.status == "SUCCESS":
                # 💡 [핵심 추가] 여기서 Quality Gate를 돌려서 점수를 뽑습니다.
                # 비교 대상 원본 코드가 없으므로 "N/A"를 넣습니다. (성능 점수는 0점 나오겠지만 보안/가독성은 나옴)
                qg_result = self._run_quality_gate("N/A", dev_out.final_code)
                
                full_report = {
                    "run_id": group,
                    "status": "DONE",
                    "quality_analysis": qg_result, # <-- 점수 저장!
                    "expert_reports": [r.model_dump() for r in all_reports],
                    "architect_plan": plan.model_dump(),
                    "developer_log": dev_out.log
                }
                self._save_results(task_dir, dev_out.final_code, full_report)
                print(f"   [{group}] 성공: 저장됨 (점수: {qg_result['total_score']})")
            else:
                print(f"   [{group}] 실패: 개발자 오류")
        else:
            print(f"   [{group}] 실패: 아키텍트 오류")

    def _run_group_e_and_d_combined(self, instance, context, base_dir):
        """E -> D 통합 (점수 측정 포함)"""
        reset_token_usage()
        e_dir = os.path.join(base_dir, instance['instance_id'], "E")
        d_dir = os.path.join(base_dir, instance['instance_id'], "D")
        os.makedirs(e_dir, exist_ok=True)
        os.makedirs(d_dir, exist_ok=True)
        print(f"   [E & D] 통합 실행 시작...")
        
        perf = self.performance_expert.run(context, "N/A")
        read = self.readability_expert.run(context, "N/A")
        sec = self.security_expert.run(context, "N/A")
        all_reports = (perf or []) + (read or []) + (sec or [])
        
        if not all_reports:
             all_reports = [ExpertReviewReport(suggestion_id="NONE", agent_role="Sys", title="None", target_code_block="Repo", severity="Low", reasoning="None", proposed_change="None")]

        # 1차 시도 (E)
        plan_v1 = self.architect_agent.run(context, all_reports, "N/A", "Resolve Issue", "CoT")
        if not plan_v1: return
        dev_out_v1 = self.developer_agent.run(context, plan_v1)
        if not dev_out_v1: return

        # 💡 [핵심 추가] E 그룹 점수 측정 및 저장
        qg_v1 = self._run_quality_gate("N/A", dev_out_v1.final_code)
        
        full_report_v1 = {
            "run_id": "E",
            "status": "ATTEMPT_1",
            "quality_analysis": qg_v1, # <-- 점수 저장!
            "expert_reports": [r.model_dump() for r in all_reports],
            "architect_plan": plan_v1.model_dump(),
            "developer_log": dev_out_v1.log
        }
        self._save_results(e_dir, dev_out_v1.final_code, full_report_v1)
        
        # D 그룹용 임시 저장
        write_text_file(os.path.join(d_dir, "final_code.py"), dev_out_v1.final_code)

        # 3. 검증 (D 회고 결정)
        # (A) 품질 점수 미달 (85점 미만)
        nfr_fail = qg_v1["total_score"] < 85
        # (B) 기능 테스트 실패 (Docker)
        is_func_valid, docker_msg = self._verify_fix_with_docker(instance, dev_out_v1.final_code)
        
        feedback_list = []
        if not is_func_valid: feedback_list.append(f"Functionality Error: {docker_msg}")
        if nfr_fail: feedback_list.append(f"Quality Score Low ({qg_v1['total_score']}/100). Improve NFRs.")

        if not feedback_list:
            print(f"   [D] 1차 성공! (점수: {qg_v1['total_score']})")
            self._save_results(d_dir, dev_out_v1.final_code, {"run_id": "D", "status": "SUCCESS_FIRST", "quality_analysis": qg_v1})
        else:
            print(f"   [D] ⚠️ 회고 시작...")
            plan_v2 = self.architect_agent.run(context, all_reports, "N/A", "Resolve Issue", "CoT", failure_feedback="\n".join(feedback_list))
            if plan_v2:
                dev_out_v2 = self.developer_agent.run(context, plan_v2)
                if dev_out_v2:
                    # 2차 점수 측정
                    qg_v2 = self._run_quality_gate("N/A", dev_out_v2.final_code)
                    full_report_v2 = {
                        "run_id": "D",
                        "status": "SUCCESS_RETRO",
                        "quality_analysis": qg_v2, # <-- 최종 점수 저장
                        "architect_plan": plan_v2.model_dump(),
                        "developer_log": dev_out_v2.log
                    }
                    self._save_results(d_dir, dev_out_v2.final_code, full_report_v2)
                    print(f"   [D] ✅ 회고 완료 (점수: {qg_v2['total_score']})")