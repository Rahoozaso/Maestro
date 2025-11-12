import pytest
from unittest.mock import patch

# --- 필요한 모든 클래스를 정확하게 import ---
from maestro.core.main_controller import MainController
from maestro.core.data_models import (
    ExpertReviewReport,
    IntegratedExecutionPlan,
    DeveloperAgentOutput
)
from maestro.agents.expert_agents import PerformanceExpert, ReadabilityExpert, SecurityExpert
from maestro.agents.architect_agent import ArchitectAgent
from maestro.agents.developer_agent import DeveloperAgent
# ----------------------------------------

# --- 테스트를 위한 기본 데이터 ---

DUMMY_CONFIG = {
    "llm": {"provider": "mock"},
    "paths": {"prompt_template_dir": "data/prompts/", "output_dir": "outputs/"},
    # --- 컨트롤러가 config.yml에서 읽을 것으로 예상하는 최소한의 설정 추가 ---
    "maestro_framework": {
        "quality_gate": {"success_threshold": 85},
        "scoring_rubric": {
            "weights": {"security": 40, "readability": 30, "performance": 30},
            "security": {
                "high_severity_score": 0,
                "medium_severity_score": 15,
                "low_severity_score": 30,
                "no_issues_score": 40
            },
            "readability": {
                "thresholds": [
                    {"max_complexity": 10, "points": 30},
                    {"max_complexity": 20, "points": 15}
                ]
            },
            "performance": {
                "improvement_thresholds": [
                    {"min_improvement_percent": 15, "points": 30},
                    {"min_improvement_percent": 5, "points": 15},
                    {"min_improvement_percent": 0, "points": 5}
                ]
            }
        }
    }
}

DUMMY_CODE = "def sample_function(): pass"
DUMMY_UNIT_TESTS = "assert sample_function() is None"

MOCK_EXPERT_REPORTS = [ExpertReviewReport(
    suggestion_id="TEST-001", agent_role="PerformanceExpert", title="Test",
    target_code_block="test.py#L1", severity="Medium", reasoning="...", proposed_change="..."
)]
MOCK_PLAN = IntegratedExecutionPlan(
    work_order_id="WO-MOCK-001", synthesis_goal="Balance", instructions=[]
)
MOCK_DEV_OUTPUT = DeveloperAgentOutput(
    status="SUCCESS", final_code="def new_function(): pass", log=[]
)

# --- 테스트 픽스처(Fixture) ---

@pytest.fixture
def mock_agents(mocker):
    """모든 에이전트의 run 메소드를 모의 처리하는 픽스처"""
    mocker.patch('maestro.agents.expert_agents.PerformanceExpert.run', return_value=MOCK_EXPERT_REPORTS)
    mocker.patch('maestro.agents.expert_agents.ReadabilityExpert.run', return_value=[])
    mocker.patch('maestro.agents.expert_agents.SecurityExpert.run', return_value=[])
    mocker.patch('maestro.agents.architect_agent.ArchitectAgent.run', return_value=MOCK_PLAN)
    mocker.patch('maestro.agents.developer_agent.DeveloperAgent.run', return_value=MOCK_DEV_OUTPUT)
    
    return {
        "perf": PerformanceExpert.run,
        "read": ReadabilityExpert.run,
        "sec": SecurityExpert.run,
        "arch": ArchitectAgent.run,
        "dev": DeveloperAgent.run
    }

# --- 테스트 클래스 ---

# 불필요한 read_yaml_file 패치 제거
@patch('maestro.core.main_controller.write_text_file')
@patch('maestro.core.main_controller.MainController._save_results')
class TestMainController:
    """MainController의 통합 워크플로우를 테스트합니다."""

    def test_workflow_success_at_first_attempt(self, mock_save, mock_write, mock_agents): # <<< mock_yaml 인자 삭제
        """
        [성공] 첫 번째 시도에서 품질 기준을 통과하여 워크플로우가 성공적으로 종료되는 경우
        """
        # 1. 준비
        with patch('maestro.core.main_controller.read_text_file', side_effect=[DUMMY_CODE, DUMMY_UNIT_TESTS]):
            with patch.object(MainController, '_run_quality_gate', return_value={"total_score": 90, "scores": {"security": 40}}) as mock_quality_gate:

                # 2. 실행
                controller = MainController(DUMMY_CONFIG)
                controller.run_workflow(
                    "dummy_code.py", 
                    "dummy_test.py", 
                    output_dir="./test_output/success" # <<< output_dir 인자 추가
                )

                # 3. 검증
                mock_agents["perf"].assert_called_once()
                mock_agents["read"].assert_called_once()
                mock_agents["sec"].assert_called_once()
                mock_agents["arch"].assert_called_once()
                mock_agents["dev"].assert_called_once()
                mock_quality_gate.assert_called_once()
                assert mock_agents["arch"].call_count == 1
                assert mock_agents["dev"].call_count == 1
                mock_save.assert_called_once()

    def test_workflow_success_after_retrospection(self, mock_save, mock_write, mock_agents): # <<< mock_yaml 인자 삭제
        """
        [성공] 첫 시도에 실패했지만, 자기 회고 루프 이후 성공하는 경우
        """
        # 1. 준비
        with patch('maestro.core.main_controller.read_text_file', side_effect=[DUMMY_CODE, DUMMY_UNIT_TESTS, DUMMY_CODE, DUMMY_UNIT_TESTS]):
            with patch.object(MainController, '_run_quality_gate', side_effect=[
                {"total_score": 50, "scores": {"security": 15}},
                {"total_score": 95, "scores": {"security": 40}}
            ]) as mock_quality_gate:

                # 2. 실행
                controller = MainController(DUMMY_CONFIG)
                controller.run_workflow(
                    "dummy_code.py", 
                    "dummy_test.py", 
                    output_dir="./test_output/retro_success", # <<< output_dir 인자 추가
                    enable_retrospection=True # 자기 회고 활성화 명시 (기본값)
                )

                # 3. 검증
                mock_agents["perf"].assert_called_once()
                mock_agents["read"].assert_called_once()
                mock_agents["sec"].assert_called_once()
                assert mock_agents["arch"].call_count == 2
                assert mock_agents["dev"].call_count == 2
                assert mock_quality_gate.call_count == 2
                mock_save.assert_called_once()