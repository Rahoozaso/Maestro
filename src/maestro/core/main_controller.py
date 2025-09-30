import os
import datetime
import json
from typing import Dict, Any

# --- 유틸리티 및 설정 ---
from maestro.utils.file_io import read_yaml_file, read_text_file, write_text_file
from maestro.utils.llm_handler import set_llm_provider

# --- 에이전트 ---
from maestro.agents.expert_agents import PerformanceExpert, ReadabilityExpert, SecurityExpert
from maestro.agents.architect_agent import ArchitectAgent
from maestro.agents.developer_agent import DeveloperAgent

# --- 분석 도구 ---
from maestro.tools.performance_profiler import profile_performance
from maestro.tools.readability_analyzer import analyze_readability
from maestro.tools.security_analyzer import analyze_security


class MainController:
    """
    MAESTRO 프레임워크의 전체 워크플로우를 조율하는 메인 컨트롤러입니다.
    """
    def __init__(self, config: Dict[str, Any]):
        """
        컨트롤러를 초기화하고 모든 에이전트를 생성합니다.

        Args:
            config (Dict[str, Any]): 'config.yml'에서 로드된 설정 딕셔너리.
        """
        self.config = config
        set_llm_provider(config['llm'])  # LLM 핸들러에 API 키 등 설정 전달

        # 에이전트 인스턴스화
        self.performance_expert = PerformanceExpert(config)
        self.readability_expert = ReadabilityExpert(config)
        self.security_expert = SecurityExpert(config)
        self.architect_agent = ArchitectAgent(config)
        self.developer_agent = DeveloperAgent(config)
        
        print("MainController 초기화 완료. 모든 에이전트가 준비되었습니다.")

    def _run_quality_gate(self, original_code: str, modified_code: str) -> Dict[str, Any]:
        """
        수정된 코드의 NFR 품질을 측정하고 점수를 매깁니다.
        """
        print("\n--- 품질 게이트 실행 ---")
        
        # 각 분석 도구 실행
        sec_report = analyze_security(modified_code)
        read_report = analyze_readability(modified_code)
        perf_report = profile_performance(original_code, modified_code)

        scores = {"security": 0, "readability": 0, "performance": 0}

        # 1. 보안 점수 계산
        if sec_report.success:
            if sec_report.highest_severity == "HIGH":
                scores["security"] = 0
            elif sec_report.highest_severity == "MEDIUM":
                scores["security"] = 15
            elif sec_report.highest_severity == "LOW":
                scores["security"] = 30
            else: # None
                scores["security"] = 40
        
        # 2. 가독성 점수 계산
        if read_report.success:
            complexity = read_report.average_complexity
            if 1 <= complexity <= 10:
                scores["readability"] = 30
            elif 11 <= complexity <= 20:
                scores["readability"] = 15
            else:
                scores["readability"] = 0

        # 3. 성능 점수 계산
        if perf_report.success:
            improvement = perf_report.improvement_percentage
            if improvement >= 15:
                scores["performance"] = 30
            elif 5 <= improvement < 15:
                scores["performance"] = 15
            elif 0 <= improvement < 5:
                scores["performance"] = 5
            else: # 성능 저하
                scores["performance"] = 0
        
        total_score = sum(scores.values())
        print(f"품질 게이트 결과: 총점 = {total_score}/100")
        print(f"  - 보안: {scores['security']}/40, 가독성: {scores['readability']}/30, 성능: {scores['performance']}/30")

        return {
            "total_score": total_score,
            "scores": scores,
            "details": {
                "security": sec_report,
                "readability": read_report,
                "performance": perf_report
            }
        }

    def _save_results(self, run_id: str, final_code: str, report: Dict[str, Any]):
        """실험 결과를 outputs 폴더에 저장합니다."""
        output_dir = os.path.join(self.config['paths']['output_dir'], run_id)
        os.makedirs(output_dir, exist_ok=True)

        # 최종 코드 저장
        write_text_file(os.path.join(output_dir, "final_code.py"), final_code)

        # 종합 리포트 저장 (JSON)
        report_path = os.path.join(output_dir, "final_report.json")
        try:
            # dataclass 객체를 JSON으로 직렬화하기 위한 처리
            def json_default(o):
                if hasattr(o, '__dict__'):
                    return o.__dict__
                raise TypeError
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=4, default=json_default, ensure_ascii=False)
            print(f"최종 결과가 '{output_dir}' 폴더에 저장되었습니다.")
        except Exception as e:
            print(f"리포트 저장 중 오류 발생: {e}")


    def run_workflow(self, source_code_path: str, unit_test_path: str):
        """
        단일 코드 파일에 대한 MAESTRO 전체 리팩토링 워크플로우를 실행합니다.
        """
        run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"\n===== MAESTRO 워크플로우 시작 (Run ID: {run_id}) =====")

        try:
            v_gen = read_text_file(source_code_path)
            unit_tests = read_text_file(unit_test_path)
        except FileNotFoundError:
            return

        # --- 1단계: 전문가 자문 ---
        print("\n--- 1단계: 전문가 자문 시작 ---")
        perf_reports = self.performance_expert.run(v_gen, unit_tests)
        read_reports = self.readability_expert.run(v_gen, unit_tests)
        sec_reports = self.security_expert.run(v_gen, unit_tests)
        
        all_reports = (perf_reports or []) + (read_reports or []) + (sec_reports or [])
        if not all_reports:
            print("모든 전문가가 개선안을 제시하지 않았습니다. 워크플로우를 종료합니다.")
            return
        print(f"총 {len(all_reports)}개의 개선안 수집 완료.")

        # --- 2단계: 아키텍트 의사결정 ---
        print("\n--- 2단계: 아키텍트 의사결정 시작 ---")
        plan = self.architect_agent.run(v_gen, all_reports, unit_tests)
        if not plan:
            print("아키텍트가 실행 계획을 생성하지 못했습니다. 워크플로우를 종료합니다.")
            return

        # --- 3단계: 개발자 구현 ---
        print("\n--- 3단계: 개발자 구현 시작 ---")
        dev_output = self.developer_agent.run(v_gen, plan)
        if not dev_output or dev_output.status == "FAILURE":
            print("개발자 에이전트가 코드 수정에 실패했습니다. 워크플로우를 종료합니다.")
            return
        
        v_final = dev_output.final_code

        # --- 4단계: 최종 품질 검증 및 자기 회고 ---
        quality_result = self._run_quality_gate(v_gen, v_final)
        final_report = {
            "run_id": run_id,
            "initial_attempt": {
                "quality": quality_result,
                "developer_log": dev_output.log
            }
        }
        
        if quality_result["total_score"] >= 85 and quality_result["scores"]["security"] > 0:
            print("\n🎉 품질 기준 충족! 리팩토링 성공.")
            self._save_results(run_id, v_final, final_report)
            return

        # 품질 기준 미달 시 자기 회고 루프 (단 1회)
        print("\n--- 4.5단계: 품질 미달, 자기 회고 루프 시작 ---")
        failure_feedback = f"1차 시도 실패. 총점: {quality_result['total_score']}. 이 피드백을 바탕으로 계획을 수정하여 다시 제출하세요."
        
        # 아키텍트 재실행
        revised_plan = self.architect_agent.run(v_gen, all_reports, unit_tests, failure_feedback=failure_feedback)
        if not revised_plan:
            print("아키텍트가 수정된 계획을 생성하지 못했습니다. 최종 실패.")
            final_report["status"] = "FINAL_FAILURE"
            self._save_results(run_id, v_final, final_report)
            return

        # 개발자 재실행
        revised_dev_output = self.developer_agent.run(v_gen, revised_plan)
        if not revised_dev_output or revised_dev_output.status == "FAILURE":
            print("개발자 에이전트가 재시도에 실패했습니다. 최종 실패.")
            final_report["status"] = "FINAL_FAILURE"
            self._save_results(run_id, v_final, final_report)
            return
            
        v_final_rev2 = revised_dev_output.final_code
        
        # 최종 품질 검증 (2차)
        final_quality_result = self._run_quality_gate(v_gen, v_final_rev2)
        final_report["retrospection_attempt"] = {
            "quality": final_quality_result,
            "developer_log": revised_dev_output.log
        }
        
        if final_quality_result["total_score"] >= 85 and final_quality_result["scores"]["security"] > 0:
            print("\n🎉 자기 회고 후 품질 기준 충족! 최종 성공.")
            final_report["status"] = "SUCCESS_AFTER_RETROSPECTION"
            self._save_results(run_id, v_final_rev2, final_report)
        else:
            print("\n❌ 자기 회고 후에도 품질 기준 미달. 최종 실패.")
            final_report["status"] = "FINAL_FAILURE"
            self._save_results(run_id, v_final, final_report) # 1차 시도 결과 저장


# --- 이 파일이 직접 실행될 때를 위한 예제 ---
if __name__ == '__main__':
    # 예제 실행을 위한 임시 파일 생성
    EXAMPLE_CODE_PATH = "example_v_gen.py"
    EXAMPLE_TEST_PATH = "example_tests.py"
    
    # AI가 생성했을 법한, 기능은 맞지만 품질이 낮은 코드 예시
    example_code = """
def find_common_elements(list1, list2):
    common = []
    for item1 in list1:
        # 성능 문제: list2를 반복적으로 순회 (O(n*m))
        if item1 in list2:
            common.append(item1)
    # 가독성 문제: 복잡한 로직이 함수 내에 직접 포함됨
    # 보안 문제: 예제에서는 간단하게 생략
    return common
"""
    
    example_tests = """
def test_find_common_elements():
    assert find_common_elements([1, 2, 3], [3, 4, 5]) == [3]
    assert find_common_elements([1, 2], [3, 4]) == []
    assert find_common_elements([1, 1, 2], [1, 3]) == [1, 1] # 중복 처리 확인
"""
    
    write_text_file(EXAMPLE_CODE_PATH, example_code)
    write_text_file(EXAMPLE_TEST_PATH, example_tests)

    try:
        # 1. 설정 파일 로드
        config = read_yaml_file("config.yml")
        
        # 2. 컨트롤러 생성 및 워크플로우 실행
        controller = MainController(config)
        controller.run_workflow(EXAMPLE_CODE_PATH, EXAMPLE_TEST_PATH)
        
    except FileNotFoundError:
        print("\n[오류] 'config.yml' 파일을 찾을 수 없습니다.")
        print("프로젝트 루트에 'config.yml.example'을 복사하여 'config.yml'을 만들고,")
        print("내부에 자신의 LLM API 키를 입력해주세요.")
    except Exception as e:
        print(f"\n워크플로우 실행 중 예상치 못한 오류 발생: {e}")
    finally:
        # 3. 임시 파일 정리
        if os.path.exists(EXAMPLE_CODE_PATH):
            os.remove(EXAMPLE_CODE_PATH)
        if os.path.exists(EXAMPLE_TEST_PATH):
            os.remove(EXAMPLE_TEST_PATH)
