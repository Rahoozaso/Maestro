import json
import pytest
from unittest.mock import patch

# Pydantic 모델과 테스트 대상 에이전트 클래스를 임포트합니다.
from maestro.core.data_models import ExpertReviewReport
from maestro.agents.expert_agents import PerformanceExpert, ReadabilityExpert, SecurityExpert

# --- 테스트를 위한 기본 데이터 ---

# 모든 테스트에서 사용할 임시 설정값입니다.
DUMMY_CONFIG = {
    "llm": {"provider": "mock"},
    "paths": {"prompt_template_dir": "data/prompt/"}
}

# 에이전트에게 분석을 요청할 임시 코드와 테스트 스위트입니다.
DUMMY_CODE_TO_ANALYZE = "def sample_function():\n    return 1+1"
DUMMY_UNIT_TESTS = "assert sample_function() == 2"

# LLM이 성공적으로 반환했다고 가정하는 유효한 JSON 데이터입니다.
VALID_REPORT_LIST_DICT = [
    {
        "suggestion_id": "TEST-001",
        "agent_role": "PerformanceExpert", # 테스트 실행 시 동적으로 변경됩니다.
        "title": "A Test Suggestion",
        "target_code_block": "sample.py#L1-L2",
        "severity": "Medium",
        "reasoning": "Because this is a test.",
        "proposed_change": "return 2"
    }
]


# --- Parametrize를 사용하여 세 에이전트의 공통 로직을 테스트 ---

@pytest.mark.parametrize("agent_class, expected_prompt_filename, agent_role", [
    (PerformanceExpert, "performance_prompt.md", "PerformanceExpert"),
    (ReadabilityExpert, "readability_prompt.md", "ReadabilityExpert"),
    (SecurityExpert, "security_prompt.md", "SecurityExpert"),
])
class TestExpertAgents:
    """
    Performance, Readability, Security 전문가 에이전트의 공통 로직을 테스트합니다.
    """

    # --- 성공 케이스 ---

    @patch('maestro.agents.expert_agents.read_text_file')
    @patch('maestro.agents.expert_agents.call_llm')
    def test_run_success(self, mock_call_llm, mock_read_file, agent_class, expected_prompt_filename, agent_role):
        """
        [성공] 프롬프트 로딩, LLM 호출, 결과 파싱 및 검증이 모두 성공하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        mock_read_file.return_value = "Code: {v_gen}\nTests: {unit_test_suite}"
        
        valid_response = VALID_REPORT_LIST_DICT.copy()
        valid_response[0]['agent_role'] = agent_role
        mock_call_llm.return_value = json.dumps(valid_response)

        agent = agent_class(DUMMY_CONFIG)

        # 2. 실행 (Act)
        reports = agent.run(DUMMY_CODE_TO_ANALYZE, DUMMY_UNIT_TESTS)

        # 3. 검증 (Assert)
        expected_path = DUMMY_CONFIG['paths']['prompt_template_dir'] + expected_prompt_filename
        mock_read_file.assert_called_once_with(expected_path)
        mock_call_llm.assert_called_once()
        
        assert isinstance(reports, list) and len(reports) == 1
        assert isinstance(reports[0], ExpertReviewReport)
        assert reports[0].agent_role == agent_role

    @patch('maestro.agents.expert_agents.read_text_file')
    @patch('maestro.agents.expert_agents.call_llm')
    def test_run_success_with_json_wrapper(self, mock_call_llm, mock_read_file, agent_class, expected_prompt_filename, agent_role):
        """
        [성공] LLM 응답이 JSON 코드 블록으로 감싸져 있어도 정상적으로 파싱하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        mock_read_file.return_value = "Code: {v_gen}\nTests: {unit_test_suite}"
        
        valid_response = VALID_REPORT_LIST_DICT.copy()
        valid_response[0]['agent_role'] = agent_role
        wrapped_response = f"Here is the report:\n```json\n{json.dumps(valid_response)}\n```"
        mock_call_llm.return_value = wrapped_response

        agent = agent_class(DUMMY_CONFIG)

        # 2. 실행 (Act)
        reports = agent.run(DUMMY_CODE_TO_ANALYZE, DUMMY_UNIT_TESTS)

        # 3. 검증 (Assert)
        assert isinstance(reports, list) and len(reports) == 1
        assert reports[0].suggestion_id == "TEST-001"

    # --- 실패 케이스 ---

    @patch('maestro.agents.expert_agents.call_llm')
    @patch('maestro.agents.expert_agents.read_text_file')
    def test_run_prompt_file_not_found(self, mock_read_file, mock_call_llm, agent_class, expected_prompt_filename, agent_role, capsys):
        """
        [실패] 프롬프트 파일을 찾지 못했을 때 빈 리스트를 반환하고 에러를 출력하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        mock_read_file.side_effect = FileNotFoundError
        agent = agent_class(DUMMY_CONFIG)

        # 2. 실행 (Act)
        reports = agent.run(DUMMY_CODE_TO_ANALYZE, DUMMY_UNIT_TESTS)

        # 3. 검증 (Assert)
        assert reports == []
        mock_call_llm.assert_not_called()
        captured = capsys.readouterr()
        assert "프롬프트 파일을 찾을 수 없습니다" in captured.out
        
    @patch('maestro.agents.expert_agents.read_text_file')
    @patch('maestro.agents.expert_agents.call_llm')
    def test_run_llm_returns_invalid_json(self, mock_call_llm, mock_read_file, agent_class, expected_prompt_filename, agent_role, capsys):
        """
        [실패] LLM이 유효하지 않은 JSON을 반환했을 때 빈 리스트를 반환하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        mock_read_file.return_value = "Code: {v_gen}\nTests: {unit_test_suite}"
        mock_call_llm.return_value = '{"key": "value", "malformed'
        agent = agent_class(DUMMY_CONFIG)

        # 2. 실행 (Act)
        reports = agent.run(DUMMY_CODE_TO_ANALYZE, DUMMY_UNIT_TESTS)
        
        # 3. 검증 (Assert)
        assert reports == []
        captured = capsys.readouterr()
        assert "LLM 응답 검증 실패" in captured.out

    @patch('maestro.agents.expert_agents.read_text_file')
    @patch('maestro.agents.expert_agents.call_llm')
    def test_run_llm_returns_invalid_schema(self, mock_call_llm, mock_read_file, agent_class, expected_prompt_filename, agent_role, capsys):
        """
        [실패] LLM이 Pydantic 모델과 맞지 않는 스키마의 JSON을 반환했을 때 빈 리스트를 반환하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        mock_read_file.return_value = "Code: {v_gen}\nTests: {unit_test_suite}"
        invalid_schema_response = [{"agent_role": agent_role, "title": "A Test Suggestion"}]
        mock_call_llm.return_value = json.dumps(invalid_schema_response)
        agent = agent_class(DUMMY_CONFIG)

        # 2. 실행 (Act)
        reports = agent.run(DUMMY_CODE_TO_ANALYZE, DUMMY_UNIT_TESTS)

        # 3. 검증 (Assert)
        assert reports == []
        captured = capsys.readouterr()
        assert "LLM 응답 검증 실패" in captured.out

# --- SecurityExpert의 특수 로직을 위한 별도 테스트 ---

def test_security_expert_handles_critical_severity(mocker):
    """
    [성공] SecurityExpert가 'Critical' 등급을 정상적으로 처리하는지 검증합니다.
    """
    # 1. 준비 (Arrange)
    mocker.patch('maestro.agents.expert_agents.read_text_file', return_value="Code: {v_gen}\nTests: {unit_test_suite}")
    mock_call_llm = mocker.patch('maestro.agents.expert_agents.call_llm')

    critical_response = VALID_REPORT_LIST_DICT.copy()
    critical_response[0]['agent_role'] = "SecurityExpert"
    critical_response[0]['severity'] = "Critical"
    mock_call_llm.return_value = json.dumps(critical_response)

    security_expert = SecurityExpert(DUMMY_CONFIG)

    # 2. 실행 (Act)
    reports = security_expert.run("some vulnerable code", DUMMY_UNIT_TESTS)

    # 3. 검증 (Assert)
    assert len(reports) == 1
    assert reports[0].severity == "Critical"

