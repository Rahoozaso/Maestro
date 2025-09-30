import pytest
from unittest.mock import patch, MagicMock

# 테스트 대상 및 필요한 데이터 모델 임포트
from maestro.core.main_controller import MainController
from maestro.core.data_models import (
    ExpertReviewReport,
    IntegratedExecutionPlan,
    DeveloperAgentOutput,
    InstructionStep
)

from maestro.agents.expert_agents import PerformanceExpert, ReadabilityExpert, SecurityExpert
from maestro.agents.architect_agent import ArchitectAgent
from maestro.agents.developer_agent import DeveloperAgent

# --- 테스트를 위한 기본 데이터 ---

# 모든 테스트에서 사용할 임시 설정값
DUMMY_CONFIG = {
    "llm": {"provider": "mock"},
    "paths": {"prompt_template_dir": "data/prompt/", "output_dir": "outputs/"}
}

# read_text_file이 반환할 가짜 코드 내용
DUMMY_CODE = "def sample_function(): pass"
DUMMY_UNIT_TESTS = "assert sample_function() is None"

# 에이전트들의 가짜 반환값
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
    
    # 각 에이전트 클래스의 run 메소드에 대한 참조를 딕셔너리로 반환
    return {
        "perf": PerformanceExpert.run,
        "read": ReadabilityExpert.run,
        "sec": SecurityExpert.run,
        "arch": ArchitectAgent.run,
        "dev": DeveloperAgent.run
    }

# --- 테스트 클래스 ---

# 모든 파일 I/O를 모의 처리하기 위해 클래스 레벨에서 patch 적용
@patch('maestro.core.main_controller.read_yaml_file', return_value=DUMMY_CONFIG)
@patch('maestro.core.main_controller.write_text_file')
@patch('maestro.core.main_controller.MainController._save_results')
class TestMainController:
    """MainController의 통합 워크플로우를 테스트합니다."""

    def test_workflow_success_at_first_attempt(self, mock_save, mock_write, mock_yaml, mock_agents):
        """
        [성공] 첫 번째 시도에서 품질 기준을 통과하여 워크플로우가 성공적으로 종료되는 경우
        """
        # 1. 준비 (Arrange)
        # read_text_file이 호출될 때 가짜 코드를 반환하도록 설정
        with patch('maestro.core.main_controller.read_text_file', side_effect=[DUMMY_CODE, DUMMY_UNIT_TESTS]):
            # 품질 게이트가 높은 점수를 반환하도록 모의 처리
            with patch.object(MainController, '_run_quality_gate', return_value={"total_score": 90, "scores": {"security": 40}}) as mock_quality_gate:

                # 2. 실행 (Act)
                controller = MainController(DUMMY_CONFIG)
                controller.run_workflow("dummy_code.py", "dummy_test.py")

                # 3. 검증 (Assert)
                # 모든 에이전트가 순서대로 한 번씩 호출되었는지 확인
                mock_agents["perf"].assert_called_once()
                mock_agents["read"].assert_called_once()
                mock_agents["sec"].assert_called_once()
                mock_agents["arch"].assert_called_once()
                mock_agents["dev"].assert_called_once()
                
                # 품질 게이트가 한 번 호출되었는지 확인
                mock_quality_gate.assert_called_once()
                
                # 자기 회고 후의 아키텍트/개발자는 호출되지 않았어야 함
                assert mock_agents["arch"].call_count == 1
                assert mock_agents["dev"].call_count == 1
                
                # 결과가 저장되었는지 확인
                mock_save.assert_called_once()

    def test_workflow_success_after_retrospection(self, mock_save, mock_write, mock_yaml, mock_agents):
        """
        [성공] 첫 시도에 실패했지만, 자기 회고 루프 이후 성공하는 경우
        """
        # 1. 준비 (Arrange)
        # read_text_file 모의 처리
        with patch('maestro.core.main_controller.read_text_file', side_effect=[DUMMY_CODE, DUMMY_UNIT_TESTS, DUMMY_CODE, DUMMY_UNIT_TESTS]):
            # 품질 게이트가 처음에는 낮은 점수, 두 번째에는 높은 점수를 반환하도록 설정
            with patch.object(MainController, '_run_quality_gate', side_effect=[
                {"total_score": 50, "scores": {"security": 15}}, # 첫 번째 호출 결과
                {"total_score": 95, "scores": {"security": 40}}  # 두 번째 호출 결과
            ]) as mock_quality_gate:

                # 2. 실행 (Act)
                controller = MainController(DUMMY_CONFIG)
                controller.run_workflow("dummy_code.py", "dummy_test.py")

                # 3. 검증 (Assert)
                # 전문가 에이전트들은 처음에 한 번만 호출됨
                mock_agents["perf"].assert_called_once()
                mock_agents["read"].assert_called_once()
                mock_agents["sec"].assert_called_once()

                # 아키텍트와 개발자가 두 번씩(초기 실행 + 회고) 호출되었는지 확인
                assert mock_agents["arch"].call_count == 2
                assert mock_agents["dev"].call_count == 2
                
                # 품질 게이트도 두 번 호출됨
                assert mock_quality_gate.call_count == 2
                
                # 결과가 저장되었는지 확인
                mock_save.assert_called_once()

