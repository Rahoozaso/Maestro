import json
from unittest.mock import patch
import sys
import os

# 프로젝트 루트 디렉토리를 시스템 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 테스트 대상인 DeveloperAgent와 데이터 모델을 import 합니다.
from maestro.agents.developer_agent import DeveloperAgent
from maestro.core.data_models import DeveloperAgentOutput

# 테스트에 사용할 가짜 설정(config)과 입력 데이터
DUMMY_CONFIG = {
    "paths": {"prompt_template_dir": "data/prompt/"},
    "llm": {"provider": "dummy"},
}
DUMMY_V_GEN = "def old_function():\n    pass"
DUMMY_PLAN = {
    "work_order_id": "WO-TEST-001",
    "target_version": "v_gen_test",
    "synthesis_goal": "Balance",
    "reasoning_log": "Test reasoning.",
    "instructions": [],
}


@patch("maestro.agents.developer_agent.call_llm")
@patch("maestro.agents.developer_agent.read_text_file")
def test_developer_agent_run_success(mock_read_file, mock_call_llm):
    """
    [성공 케이스] LLM이 유효한 JSON을 반환했을 때,
    에이전트가 이를 성공적으로 파싱하고 DeveloperAgentOutput 객체를 반환하는지 테스트합니다.
    """
    mock_read_file.return_value = "Fake prompt template"
    # 1. 모의(Mock) LLM이 반환할 가짜 응답을 설정합니다.
    expected_output_dict = {
        "status": "SUCCESS",
        "final_code": "def new_function():\n    pass",
        "log": ["Step 1: Success."],
    }
    # LLM 응답은 항상 JSON '문자열' 형태이므로, dumps를 사용합니다.
    # LLM이 코드 블록을 포함하여 응답하는 것을 시뮬레이션합니다.
    mock_response_str = f"```json\n{json.dumps(expected_output_dict)}\n```"
    mock_call_llm.return_value = mock_response_str

    # 2. 에이전트를 생성하고 실행합니다.
    agent = DeveloperAgent(DUMMY_CONFIG)
    result = agent.run(DUMMY_V_GEN, DUMMY_PLAN)

    # 3. 결과를 검증합니다.
    # 모의 LLM 함수가 정확히 한 번 호출되었는지 확인합니다.
    mock_call_llm.assert_called_once()

    # 반환된 결과가 None이 아니며, 올바른 타입인지 확인합니다.
    assert result is not None
    assert isinstance(result, DeveloperAgentOutput)

    # 결과의 내용이 우리가 모의 응답으로 설정한 값과 일치하는지 확인합니다.
    assert result.status == "SUCCESS"
    assert "new_function" in result.final_code


@patch("maestro.agents.developer_agent.read_text_file")
@patch("maestro.agents.developer_agent.call_llm")
def test_developer_agent_run_invalid_json(mock_call_llm, mock_read_file):
    """
    [실패 케이스 1] LLM이 깨진 JSON(유효하지 않은 형식)을 반환했을 때,
    에이전트가 오류를 발생시키지 않고 None을 반환하는지 테스트합니다.
    """
    mock_read_file.return_value = "Fake prompt template"
    # 1. 모의 LLM이 깨진 JSON 문자열을 반환하도록 설정합니다.
    mock_call_llm.return_value = "This is not a valid JSON"

    # 2. 에이전트를 실행합니다.
    agent = DeveloperAgent(DUMMY_CONFIG)
    result = agent.run(DUMMY_V_GEN, DUMMY_PLAN)

    # 3. 결과를 검증합니다.
    # 에러를 잘 처리하고 최종적으로 None을 반환해야 합니다.
    assert result is None


@patch("maestro.agents.developer_agent.read_text_file")
@patch("maestro.agents.developer_agent.call_llm")
def test_developer_agent_run_validation_error(mock_call_llm, mock_read_file):
    """
    [실패 케이스 2] LLM이 유효한 JSON이지만, Pydantic 모델의 스키마와 맞지 않는 데이터를 반환했을 때,
    에이전트가 ValidationError를 처리하고 None을 반환하는지 테스트합니다.
    """
    mock_read_file.return_value = "Fake prompt template"
    # 1. 'final_code'라는 필수 필드가 누락된 JSON을 반환하도록 설정합니다.
    invalid_schema_dict = {
        "status": "SUCCESS",
        # "final_code" is missing
        "log": ["Step 1: Success."],
    }
    mock_call_llm.return_value = json.dumps(invalid_schema_dict)

    # 2. 에이전트를 실행합니다.
    agent = DeveloperAgent(DUMMY_CONFIG)
    result = agent.run(DUMMY_V_GEN, DUMMY_PLAN)

    # 3. 결과를 검증합니다.
    # 스키마 검증 실패를 잘 처리하고 최종적으로 None을 반환해야 합니다.
    assert result is None
