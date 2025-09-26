# tests/test_expert_agents.py

import json
import pytest
from unittest.mock import patch, mock_open

# Pydantic 모델과 테스트 대상 에이전트 클래스를 임포트합니다.
# 실제 프로젝트 구조에 맞게 경로를 조정해야 할 수 있습니다.
from maestro.core.data_models import ExpertReviewReport
from maestro.agents.expert_agents import PerformanceExpert, ReadabilityExpert, SecurityExpert

# --- 테스트를 위한 기본 데이터 ---

# 모든 테스트에서 사용할 임시 설정값입니다.
DUMMY_CONFIG = {
    "llm": {"provider": "mock"},
    "paths": {"prompt_template_dir": "data/prompt/"}
}

# 에이전트에게 분석을 요청할 임시 코드입니다.
DUMMY_CODE_TO_ANALYZE = "def sample_function():\n    return 1+1"

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


# --- Parametrize를 사용하여 세 에이전트를 모두 테스트 ---

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

    @patch('maestro.agents.expert_agents.call_llm')
    @patch('builtins.open', new_callable=mock_open, read_data="Code: {v_gen}")
    def test_run_success(self, mock_file, mock_call_llm, agent_class, expected_prompt_filename, agent_role):
        """
        [성공] 프롬프트 로딩, LLM 호출, 결과 파싱 및 검증이 모두 성공하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        # LLM이 반환할 모의 응답을 설정합니다.
        valid_response = VALID_REPORT_LIST_DICT.copy()
        valid_response[0]['agent_role'] = agent_role # 역할에 맞는 데이터로 수정
        mock_call_llm.return_value = json.dumps(valid_response)

        agent = agent_class(DUMMY_CONFIG)

        # 2. 실행 (Act)
        reports = agent.run(DUMMY_CODE_TO_ANALYZE)

        # 3. 검증 (Assert)
        # 파일이 올바른 경로와 모드로 열렸는지 확인합니다.
        expected_path = DUMMY_CONFIG['paths']['prompt_template_dir'] + expected_prompt_filename
        mock_file.assert_called_once_with(expected_path, "r", encoding="utf-8")

        # LLM이 한 번 호출되었는지 확인합니다.
        mock_call_llm.assert_called_once()
        
        # 반환된 결과가 ExpertReviewReport 객체의 리스트인지 확인합니다.
        assert isinstance(reports, list)
        assert len(reports) == 1
        assert isinstance(reports[0], ExpertReviewReport)
        
        # 반환된 데이터의 내용이 정확한지 확인합니다.
        assert reports[0].suggestion_id == "TEST-001"
        assert reports[0].agent_role == agent_role

    # --- 실패 케이스 ---

    @patch('maestro.agents.expert_agents.call_llm')
    @patch('builtins.open')
    def test_run_prompt_file_not_found(self, mock_file, mock_call_llm, agent_class, expected_prompt_filename, agent_role, capsys):
        """
        [실패] 프롬프트 파일을 찾지 못했을 때 빈 리스트를 반환하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        # open 함수가 FileNotFoundError를 발생시키도록 설정합니다.
        mock_file.side_effect = FileNotFoundError
        agent = agent_class(DUMMY_CONFIG)

        # 2. 실행 (Act)
        reports = agent.run(DUMMY_CODE_TO_ANALYZE)

        # 3. 검증 (Assert)
        # 결과가 빈 리스트인지 확인합니다.
        assert reports == []
        # LLM은 호출되지 않았어야 합니다.
        mock_call_llm.assert_not_called()
        # 콘솔에 에러 메시지가 출력되었는지 확인합니다.
        captured = capsys.readouterr()
        assert "프롬프트 파일을 찾을 수 없습니다" in captured.out
        
    @patch('maestro.agents.expert_agents.call_llm')
    @patch('builtins.open', new_callable=mock_open, read_data="Code: {v_gen}")
    def test_run_llm_returns_invalid_json(self, mock_file, mock_call_llm, agent_class, expected_prompt_filename, agent_role, capsys):
        """
        [실패] LLM이 유효하지 않은 JSON을 반환했을 때 빈 리스트를 반환하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        # LLM이 깨진 JSON 문자열을 반환하도록 설정합니다.
        mock_call_llm.return_value = '{"key": "value", "malformed'
        agent = agent_class(DUMMY_CONFIG)

        # 2. 실행 (Act)
        reports = agent.run(DUMMY_CODE_TO_ANALYZE)
        
        # 3. 검증 (Assert)
        assert reports == []
        mock_call_llm.assert_called_once()
        captured = capsys.readouterr()
        assert "LLM 응답 검증 실패" in captured.out

    @patch('maestro.agents.expert_agents.call_llm')
    @patch('builtins.open', new_callable=mock_open, read_data="Code: {v_gen}")
    def test_run_llm_returns_invalid_schema(self, mock_file, mock_call_llm, agent_class, expected_prompt_filename, agent_role, capsys):
        """
        [실패] LLM이 Pydantic 모델과 맞지 않는 스키마의 JSON을 반환했을 때 빈 리스트를 반환하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        # 필수 필드인 'suggestion_id'가 누락된 JSON을 반환하도록 설정합니다.
        invalid_schema_response = [{
            "agent_role": agent_role,
            "title": "A Test Suggestion",
        }]
        mock_call_llm.return_value = json.dumps(invalid_schema_response)
        agent = agent_class(DUMMY_CONFIG)

        # 2. 실행 (Act)
        reports = agent.run(DUMMY_CODE_TO_ANALYZE)

        # 3. 검증 (Assert)
        assert reports == []
        mock_call_llm.assert_called_once()
        captured = capsys.readouterr()
        assert "LLM 응답 검증 실패" in captured.out