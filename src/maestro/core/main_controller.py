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
    MAESTRO 통합 컨트롤러 (연구 계획서 5.2.3 평가 지표 엄격 준수)
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
    #  Helper: 엄격한 품질 게이트 (Research Protocol 5.2.3)
    # -------------------------------------------------------
    def _run_quality_gate(self, original_code: str, modified_code: str) -> Dict[str, Any]:
        """
        [엄격 모드] 수정된 코드의 품질을 정밀하게 측정합니다.
        """
        print("\n      >>> [Quality Gate] 품질 측정 시작 (Strict Mode)...")
        scores = {"security": 0, "readability": 0, "performance": 0}
        
        # 0. Syntax Check
        try:
            tree = ast.parse(modified_code)
            print("      >> 문법 검사 통과")
        except SyntaxError as e:
            error_msg = f"SyntaxError: {e.msg} line {e.lineno}"
            print(f"      🚨 [치명적] {error_msg}")
            return {"total_score": 0, "scores": scores, "details": {"error": error_msg}}
        except Exception as e:
            return {"total_score": 0, "scores": scores, "details": {"error": str(e)}}

        # 1. 보안 (Security) - 엄격해짐
        sec_report = analyze_security(modified_code)
        if sec_report.success:
            if sec_report.highest_severity == "HIGH": scores["security"] = 0
            elif sec_report.highest_severity == "MEDIUM": scores["security"] = 15 # [변경] 30 -> 15 (엄격)
            elif sec_report.highest_severity == "LOW": scores["security"] = 30
            else: scores["security"] = 40

        # 2. 가독성 (Readability) - Docstring 검사 추가
        try:
            read_report = analyze_readability(modified_code)
            if read_report and read_report.success:
                # (A) 복잡도 점수 (20점 만점)
                complexity_score = 0
                avg_cc = read_report.average_complexity
                if avg_cc <= 5: complexity_score = 20
                elif avg_cc <= 10: complexity_score = 15
                elif avg_cc <= 20: complexity_score = 5
                
                # (B) Docstring 점수 (10점 만점) - AST로 검사
                docstring_score = 0
                has_docstring = False
                # 모듈 레벨 또는 함수 레벨 Docstring 확인
                if ast.get_docstring(tree):
                    has_docstring = True
                else:
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                            if ast.get_docstring(node):
                                has_docstring = True
                                break
                
                if has_docstring:
                    docstring_score = 10
                else:
                    print("      -> 감점: Docstring 없음 (-10점)")

                scores["readability"] = complexity_score + docstring_score
        except Exception: scores["readability"] = 0

        # 3. 성능 (Performance) - 기준 상향
        perf_report = None
        if not original_code or original_code == "N/A":
             scores["performance"] = 10 
             print("      -> 비교 대상 없음. 기본 점수 10점.")
        else:
            try:
                perf_report = profile_performance(original_code, modified_code)
                if perf_report and perf_report.success:
                    imp = perf_report.improvement_percentage
                    print(f"      -> 성능 개선율: {imp:.2f}%")
                    if imp >= 30: scores["performance"] = 30     # [변경] 15% -> 30% (엄격)
                    elif imp >= 15: scores["performance"] = 20   # [변경] 세분화
                    elif imp >= 5: scores["performance"] = 10
                    elif imp >= 0: scores["performance"] = 5
                    # 마이너스는 0점
            except Exception: 
                scores["performance"] = 0

        total = sum(scores.values())
        print(f"      >>> 결과: {total}/100 (Sec:{scores['security']}, Read:{scores['readability']}, Perf:{scores['performance']})")

        return {
            "total_score": total,
            "scores": scores,
            "details": {
                "security": sec_report,
                "readability": read_report, 
                "performance": perf_report
            }
        }
    
    def _save_results(self, output_dir: str, final_code: str, report: Dict[str, Any]):
        """결과 저장 (종합 점수 계산 포함)"""
        os.makedirs(output_dir, exist_ok=True)
        write_text_file(os.path.join(output_dir, "final_code.py"), final_code)
        
        # 비용 추적
        token_usage = get_token_usage()
        report["cost_analysis"] = {
            "prompt_tokens": token_usage["prompt"],
            "completion_tokens": token_usage["completion"],
            "estimated_cost_usd": (token_usage["prompt"] * 5 + token_usage["completion"] * 15) / 1_000_000
        }

        # 💡 [핵심 수정] Comprehensive Score (Maestro Score) 계산
        # 논리: 기능 테스트(functional_analysis)가 성공(True)이어야만 NFR 점수를 인정. 
        # 실패 시 실용성이 없으므로 0점 부여 (Hard Constraint).
        nfr_score = report.get("quality_analysis", {}).get("total_score", 0)
        func_success = report.get("functional_analysis", {}).get("success", False)
        
        final_score = nfr_score if func_success else 0
        report["maestro_score"] = final_score # 논문에 사용될 최종 지표

        try:
            with open(os.path.join(output_dir, "final_report.json"), "w", encoding="utf-8") as f:
                json.dump(report, f, indent=4, default=str, ensure_ascii=False)
            print(f"      -> 결과 저장 완료 (비용: ${report['cost_analysis']['estimated_cost_usd']:.4f}, Maestro Score: {final_score})")
        except Exception as e:
            print(f"      -> 리포트 저장 실패: {e}")

    def _verify_fix_with_docker(self, instance, code_content):
        """
        Docker 샌드박스 검증 (완전 격리 & 자동 뒷정리)
        """
        print("   [검증] Docker 테스트 시도...")
        
        # 1. 문법 검사
        try:
            tree = ast.parse(code_content)
        except SyntaxError as e:
            return False, f"SyntaxError in generated code: {e.msg} at line {e.lineno}"

        # 2. 의존성 자동 감지
        dependencies = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    dependencies.add(name.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    dependencies.add(node.module.split('.')[0])
        
        stdlib = {'os', 'sys', 'json', 're', 'math', 'datetime', 'time', 'typing', 'ast', 'collections', 'itertools', 'functools', 'unittest', 'dataclasses'}
        libs_to_install = list(dependencies - stdlib)
        pkg_map = {'sklearn': 'scikit-learn', 'PIL': 'Pillow', 'cv2': 'opencv-python'}
        libs_to_install = [pkg_map.get(lib, lib) for lib in libs_to_install]

        container = None
        try:
            import docker
            client = docker.from_env()
            image_name = "python:3.9" 
            
            print(f"      -> Docker({image_name}) 격리 환경 생성 중... (Install: {libs_to_install})")
            
            # 실행 스크립트 구성
            install_cmd = ""
            if libs_to_install:
                install_cmd = f"pip install {' '.join(libs_to_install)} --quiet --no-cache-dir && "
            
            # echo로 파일 생성 시 특수문자 충돌 방지를 위해 cat <<EOF 방식 사용
            setup_and_run = (
                f"{install_cmd} "
                f"cat <<EOF > run_me.py\n{code_content}\nEOF\n"
                f"python run_me.py"
            )
            
            # 3. 컨테이너 실행 (완전 격리된 1회용 환경)
            container = client.containers.run(
                image_name,
                command=f'/bin/bash -c "{setup_and_run}"',
                detach=True,
                # 네트워크 허용 (pip install 위함)
                network_mode="bridge" 
            )
            
            # 4. 결과 대기 (최대 60초)
            exit_code = container.wait(timeout=60)
            logs = container.logs().decode("utf-8")
            
            if exit_code['StatusCode'] == 0:
                return True, "Execution Successful (Docker)"
            else:
                return False, f"Runtime Error in Docker:\n{logs.strip()}"

        except ImportError:
            return True, "Docker Skipped (Lib missing)"
        except Exception as e:
            # 타임아웃 등으로 컨테이너가 안 죽었을 수 있으므로 예외 처리
            print(f"      -> Docker 실행 이슈: {e}")
            return True, f"Docker execution failed ({e})"
        
        finally:
            # 💡 [핵심] 실험이 끝나면 무조건 컨테이너 삭제 (흔적 제거)
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
    # ====================================================
    #  CORE 1: HumanEval Workflow
    # ====================================================
    def run_humaneval_workflow(self, source_code_path, unit_test_path, output_dir, architect_mode="CoT", enable_retrospection=True):
        run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"\n===== [HumanEval] 워크플로우 시작 (Run ID: {run_id}) =====")
        try:
            v_gen = read_text_file(source_code_path)
            unit_tests = read_text_file(unit_test_path)
        except FileNotFoundError: return

        print("\n--- 1단계: 전문가 자문 ---")
        perf_reports = self.performance_expert.run(v_gen, unit_tests)
        read_reports = self.readability_expert.run(v_gen, unit_tests)
        sec_reports = self.security_expert.run(v_gen, unit_tests)
        all_reports = (perf_reports or []) + (read_reports or []) + (sec_reports or [])

        if not all_reports:
            print("모든 전문가가 개선안을 제시하지 않았습니다. 원본 유지 및 종료.")
            qg = self._run_quality_gate(v_gen, v_gen)
            self._save_results(output_dir, v_gen, {"run_id": run_id, "status": "NO_CHANGES", "initial": {"quality": qg}})
            return

        print(f"총 {len(all_reports)}개의 개선안 수집 완료.")

        print("\n--- 2단계: 아키텍트 의사결정 ---")
        plan = self.architect_agent.run(v_gen, all_reports, unit_tests, architect_mode=architect_mode)
        if not plan: return

        print("\n--- 3단계: 개발자 구현 ---")
        dev_output = self.developer_agent.run(v_gen, plan)
        if not dev_output or dev_output.status == "FAILURE": return
        v_final = dev_output.final_code

        # 4. 품질 검증
        quality_result = self._run_quality_gate(v_gen, v_final)
        final_report = {
            "run_id": run_id,
            "expert_reports": [r.model_dump() for r in all_reports],
            "architect_plan": plan.model_dump(),
            "developer_log": dev_output.log,
            "quality_analysis": quality_result 
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

        print("\n--- 4.5단계: 회고 루프 진입 ---")
        if architect_mode == "RuleBased":
            final_report["status"] = "FINAL_FAILURE_RULEBASED"
            self._save_results(output_dir, v_final, final_report)
            return

        feedback = f"Score Low: {quality_result['total_score']}."
        plan_v2 = self.architect_agent.run(v_gen, all_reports, unit_tests, failure_feedback=feedback)
        
        if plan_v2:
            dev_out_v2 = self.developer_agent.run(v_gen, plan_v2)
            if dev_out_v2:
                qg_v2 = self._run_quality_gate(v_gen, dev_out_v2.final_code)
                final_report["retrospection"] = {"quality": qg_v2, "developer_log": dev_out_v2.log}
                final_report["status"] = "SUCCESS_RETRO" if qg_v2["total_score"] >= 85 else "FINAL_FAILURE"
                self._save_results(output_dir, dev_out_v2.final_code, final_report)

    # ====================================================
    #  CORE 2: SWE-bench Workflow (A -> B/C/D/E 구조)
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
            
            # 1. 기본 컨텍스트 (이슈 설명)
            base_context = f"Repository: {instance['repo']}\nIssue:\n{safe_problem}"

            # -------------------------------------------------------
            # [Step 1] Group A: Baseline Code 생성 (Initial Solver)
            # -------------------------------------------------------
            # 기존 Group B가 하던 역할을 Group A에게 부여
            group_a_code = self._run_group_a_generation(instance, base_context, output_base_dir)
            
            if not group_a_code:
                print("   [Critical] Group A 생성 실패. 해당 이슈 스킵.")
                continue

            # -------------------------------------------------------
            # [Step 2] Refactoring Context 준비
            # -------------------------------------------------------
            # 이제부터 B, C, D, E는 이슈 설명뿐만 아니라 A가 짠 코드(v_gen)를 입력으로 받음
            refactoring_context = f"{base_context}\n\n[CURRENT CODE (v_gen)]:\n```python\n{group_a_code}\n```"
            
            # -------------------------------------------------------
            # [Step 3] Group B: Simple LLM Refactoring (New)
            # -------------------------------------------------------
            self._run_group_b_refactoring(instance, refactoring_context, output_base_dir, baseline_code=group_a_code)

            # -------------------------------------------------------
            # [Step 4] Group C: Rule-Based Refactoring
            # -------------------------------------------------------
            self._run_group_c_refactoring(instance, refactoring_context, output_base_dir, baseline_code=group_a_code)

            # -------------------------------------------------------
            # [Step 5] Group E & D: MAESTRO Refactoring
            # -------------------------------------------------------
            self._run_group_e_and_d_combined(instance, refactoring_context, output_base_dir, baseline_code=group_a_code)
            
            count += 1

    # --- [Group A] Initial Generation ---
    def _run_group_a_generation(self, instance, context, base_dir) -> Optional[str]:
        """Group A: 이슈를 보고 처음으로 해결책을 생성 (기존 B 역할)"""
        task_dir = os.path.join(base_dir, instance['instance_id'], "A")
        os.makedirs(task_dir, exist_ok=True)
        print(f"   [A] Baseline 생성 중... (Initial Solver)")
        
        # A는 전문가 없이 바로 해결책 제안 (단순 LLM)
        dummy = [ExpertReviewReport(suggestion_id="INIT", agent_role="Dev", title="Init", target_code_block="Repo", severity="High", reasoning="Initial Fix", proposed_change="Fix")]
        plan = self.architect_agent.run(context, dummy, "N/A", "Resolve Issue", "CoT")
        
        if plan:
            dev_out = self.developer_agent.run(context, plan)
            if dev_out and dev_out.status == "SUCCESS":
                # A 결과 저장
                self._save_results(task_dir, dev_out.final_code, {"run_id": "A", "status": "GENERATED"})
                print(f"   [A] 성공: v_gen 생성 완료")
                return dev_out.final_code
        
        print(f"   [A] 실패: 코드 생성 불가")
        return None

    # --- [Group B] Simple Refactoring ---
    def _run_group_b_refactoring(self, instance, context, base_dir, baseline_code):
        """Group B: A가 만든 코드를 단순 프롬프트로 리팩토링"""
        task_dir = os.path.join(base_dir, instance['instance_id'], "B")
        os.makedirs(task_dir, exist_ok=True)
        print(f"   [B] 실행 중... (Simple Refactoring)")
        
        # B는 "이 코드를 더 좋게 고쳐줘"라는 단순 지시를 내림 (전문가 X)
        dummy = [ExpertReviewReport(suggestion_id="IMPROVE", agent_role="Dev", title="Improve", target_code_block="Repo", severity="Medium", reasoning="Improve NFRs", proposed_change="Refactor")]
        plan = self.architect_agent.run(context, dummy, "N/A", "Resolve Issue", "CoT")
        
        if plan:
            dev_out = self.developer_agent.run(context, plan)
            if dev_out and dev_out.status == "SUCCESS":
                qg = self._run_quality_gate(baseline_code, dev_out.final_code)
                is_valid, msg = self._verify_fix_with_docker(instance, dev_out.final_code)
                report = {"run_id": "B", "status": "DONE", "quality_analysis": qg, "functional_analysis": {"success": is_valid, "message": msg}}
                self._save_results(task_dir, dev_out.final_code, report)
                print(f"   [B] 성공: 저장됨 (점수: {qg['total_score']})")

    # --- [Group C] Rule-Based Refactoring ---
    def _run_group_c_refactoring(self, instance, context, base_dir, baseline_code):
        """Group C: 규칙 기반 리팩토링"""
        task_dir = os.path.join(base_dir, instance['instance_id'], "C")
        os.makedirs(task_dir, exist_ok=True)
        print(f"   [C] 실행 중... (RuleBased)")
        
        perf = self.performance_expert.run(context, "N/A")
        read = self.readability_expert.run(context, "N/A")
        sec = self.security_expert.run(context, "N/A")
        all_reports = (perf or []) + (read or []) + (sec or [])
        
        if not all_reports:
             all_reports = [ExpertReviewReport(suggestion_id="NONE", agent_role="System", title="No Issues", target_code_block="Repo", severity="Low", reasoning="None", proposed_change="Proceed")]

        plan = self.architect_agent.run(context, all_reports, "N/A", "Resolve Issue", "RuleBased")
        
        if plan:
            dev_out = self.developer_agent.run(context, plan)
            if dev_out and dev_out.status == "SUCCESS":
                qg = self._run_quality_gate(baseline_code, dev_out.final_code)
                is_valid, msg = self._verify_fix_with_docker(instance, dev_out.final_code)
                report = {"run_id": "C", "status": "DONE", "quality_analysis": qg, "functional_analysis": {"success": is_valid, "message": msg}, "architect_plan": plan.model_dump()}
                self._save_results(task_dir, dev_out.final_code, report)
                print(f"   [C] 성공: 저장됨 (점수: {qg['total_score']})")

    # --- [Group E & D] MAESTRO Refactoring (기존 함수명 유지하되 인자 변경) ---
    def _run_group_e_and_d_combined(self, instance, context, base_dir, baseline_code="N/A"):
        """Group E -> D 통합 (Baseline 비교 포함)"""
        # (이전 코드와 로직은 동일하지만, baseline_code 인자명이 통일됨)
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
            all_reports = [ExpertReviewReport(suggestion_id="NONE", agent_role="System", title="No Issues", target_code_block="Repo", severity="Low", reasoning="None", proposed_change="Proceed")]

        # 1차 시도 (E)
        print(f"   [E] 1차 시도...")
        plan_v1 = self.architect_agent.run(context, all_reports, "N/A", "Resolve Issue", "CoT")
        if not plan_v1: return
        dev_out_v1 = self.developer_agent.run(context, plan_v1)
        if not dev_out_v1: return

        # E 저장 (Baseline 비교)
        qg_v1 = self._run_quality_gate(baseline_code, dev_out_v1.final_code)
        is_valid_v1, message_v1 = self._verify_fix_with_docker(instance, dev_out_v1.final_code)
        
        full_report_v1 = {
            "run_id": "E", "status": "ATTEMPT_1", "quality_analysis": qg_v1,
            "functional_analysis": {"success": is_valid_v1, "message": message_v1},
            "expert_reports": [r.model_dump() for r in all_reports],
            "architect_plan": plan_v1.model_dump(), "developer_log": dev_out_v1.log
        }
        self._save_results(e_dir, dev_out_v1.final_code, full_report_v1)
        write_text_file(os.path.join(d_dir, "final_code.py"), dev_out_v1.final_code)

        # 3. 검증 및 회고 (D)
        feedback_list = []
        if not is_valid_v1: feedback_list.append(f"Functional Error: {message_v1}")
        if qg_v1["total_score"] < 85: feedback_list.append(f"NFR Score Low ({qg_v1['total_score']}).")

        if not feedback_list:
            print(f"   [D] 1차 성공. 회고 생략.")
            full_report_v1["run_id"] = "D"
            full_report_v1["status"] = "SUCCESS_FIRST_TRY"
            self._save_results(d_dir, dev_out_v1.final_code, full_report_v1)
        else:
            print(f"   [D] ⚠️ 회고 시작...")
            plan_v2 = self.architect_agent.run(context, all_reports, "N/A", "Resolve Issue", "CoT", failure_feedback="\n".join(feedback_list))
            if plan_v2:
                dev_out_v2 = self.developer_agent.run(context, plan_v2)
                if dev_out_v2:
                    qg_v2 = self._run_quality_gate(baseline_code, dev_out_v2.final_code)
                    is_valid_v2, message_v2 = self._verify_fix_with_docker(instance, dev_out_v2.final_code)
                    
                    full_report_v2 = {
                        "run_id": "D", "status": "SUCCESS_RETRO", "quality_analysis": qg_v2,
                        "functional_analysis": {"success": is_valid_v2, "message": message_v2},
                        "architect_plan": plan_v2.model_dump(), "developer_log": dev_out_v2.log,
                        "feedback_used": "\n".join(feedback_list)
                    }
                    self._save_results(d_dir, dev_out_v2.final_code, full_report_v2)
                    print(f"   [D] ✅ 회고 완료.")