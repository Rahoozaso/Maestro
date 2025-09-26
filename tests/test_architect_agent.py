# tests/test_architect_agent.py

import json
import pytest
from unittest.mock import patch, mock_open

# Pydantic 모델과 테스트 대상 에이전트 클래스를 임포트합니다.
from maestro.core.data_models import ExpertReviewReport, IntegratedExecutionPlan
from maestro.agents.architect_agent import ArchitectAgent

# --- 테스트를 위한 기본 데이터 ---

DUMMY_CONFIG = {
    "llm": {"provider": "mock"},
    "paths": {"prompt_template_dir": "data/prompt/"}
}
DUMMY_V_GEN = "def original_function():\n    pass"
DUMMY_UNIT_TEST_SUITE = "assert original_function() is None"

# 테스트에 사용할 전문가 리포트 객체 리스트입니다.
DUMMY_EXPERT_REPORTS = [
    ExpertReviewReport(
        suggestion_id="PERF-001",
        agent_role="PerformanceExpert",
        title="Use list comprehension",
        target_code_block="file.py#L1-L5",
        severity="Medium",
        reasoning="It is faster.",
        proposed_change="[i for i in range(10)]"
    )
]

# LLM이 성공적으로 반환했다고 가정하는 유효한 실행 계획 데이터입니다.
VALID_PLAN_DICT = {
    "work_order_id": "WO-12345",
    "synthesis_goal": "Balance",
    "instructions": [
        {
            "step": 1,
            "description": "Replace the for-loop with a list comprehension.",
            "action": "REPLACE",
            "target_code_block": "file.py#L1-L5",
            "new_code": "[i for i in range(10)]",
            "source_suggestion_ids": ["PERF-001"],
            "rationale": "Improves performance as requested by PERF-001."
        }
    ]
}

# --- ArchitectAgent 테스트 클래스 ---

class TestArchitectAgent:
    """
    ArchitectAgent의 동작을 검증하는 테스트 스위트입니다.
    """

    # --- 성공 케이스 ---

    @pytest.mark.parametrize("llm_response_format", [
        # LLM 응답이 코드 블록에 싸여 있는 경우
        "```json\n{0}\n```",
        # LLM 응답이 순수 JSON 문자열인 경우
        "{0}"
    ])
    @patch('maestro.agents.architect_agent.call_llm')
    @patch('builtins.open', new_callable=mock_open, read_data="Prompt: {v_gen}, Reports: {expert_reports}")
    def test_run_success(self, mock_file, mock_call_llm, llm_response_format):
        """
        [성공] LLM이 유효한 실행 계획을 반환했을 때, 성공적으로 파싱하고 검증하는지 테스트합니다.
        다양한 LLM 응답 형식(코드 블록 포함/미포함)을 모두 테스트합니다.
        """
        # 1. 준비 (Arrange)
        response_json_str = json.dumps(VALID_PLAN_DICT)
        mock_call_llm.return_value = llm_response_format.format(response_json_str)
        agent = ArchitectAgent(DUMMY_CONFIG)

        # 2. 실행 (Act)
        plan = agent.run(DUMMY_V_GEN, DUMMY_EXPERT_REPORTS, DUMMY_UNIT_TEST_SUITE)

        # 3. 검증 (Assert)
        # 파일이 올바른 경로로 열렸는지 확인
        expected_path = DUMMY_CONFIG['paths']['prompt_template_dir'] + "architect_prompt.md"
        mock_file.assert_called_once_with(expected_path, "r", encoding="utf-8")
        
        # LLM이 한 번 호출되었는지 확인
        mock_call_llm.assert_called_once()

        # 반환된 결과가 IntegratedExecutionPlan 객체인지 확인
        assert isinstance(plan, IntegratedExecutionPlan)
        assert plan.work_order_id == "WO-12345"
        assert len(plan.instructions) == 1
        assert plan.instructions[0].step == 1

    # --- 실패 케이스 ---

    @patch('builtins.open')
    def test_run_prompt_file_not_found(self, mock_file, capsys):
        """
        [실패] 아키텍트 프롬프트 파일을 찾지 못했을 때 None을 반환하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        mock_file.side_effect = FileNotFoundError
        agent = ArchitectAgent(DUMMY_CONFIG)

        # 2. 실행 (Act)
        result = agent.run(DUMMY_V_GEN, DUMMY_EXPERT_REPORTS, DUMMY_UNIT_TEST_SUITE)

        # 3. 검증 (Assert)
        assert result is None
        captured = capsys.readouterr()
        assert "아키텍트 프롬프트 파일을 찾을 수 없습니다" in captured.out

    @patch('maestro.agents.architect_agent.call_llm')
    @patch('builtins.open', new_callable=mock_open, read_data="test prompt")
    def test_run_llm_api_error(self, mock_file, mock_call_llm, capsys):
        """
        [실패] LLM API 호출 중 예외가 발생했을 때 None을 반환하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        mock_call_llm.side_effect = Exception("API limit reached")
        agent = ArchitectAgent(DUMMY_CONFIG)

        # 2. 실행 (Act)
        result = agent.run(DUMMY_V_GEN, DUMMY_EXPERT_REPORTS, DUMMY_UNIT_TEST_SUITE)

        # 3. 검증 (Assert)
        assert result is None
        captured = capsys.readouterr()
        assert "LLM API 호출 중 오류 발생" in captured.out

    @patch('maestro.agents.architect_agent.call_llm')
    @patch('builtins.open', new_callable=mock_open, read_data="test prompt")
    def test_run_invalid_json_response(self, mock_file, mock_call_llm, capsys):
        """
        [실패] LLM이 깨진 JSON을 반환했을 때 None을 반환하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        mock_call_llm.return_value = "This is not JSON ```json { broken"
        agent = ArchitectAgent(DUMMY_CONFIG)

        # 2. 실행 (Act)
        result = agent.run(DUMMY_V_GEN, DUMMY_EXPERT_REPORTS, DUMMY_UNIT_TEST_SUITE)

        # 3. 검증 (Assert)
        assert result is None
        captured = capsys.readouterr()
        assert "LLM 응답 검증에 실패했습니다" in captured.out
        assert "LLM 원본 응답" in captured.out # 원본 응답을 출력하는지 확인

    @patch('maestro.agents.architect_agent.call_llm')
    @patch('builtins.open', new_callable=mock_open, read_data="test prompt")
    def test_run_invalid_schema_response(self, mock_file, mock_call_llm, capsys):
        """
        [실패] LLM이 필수 필드가 누락된 유효한 JSON을 반환했을 때 None을 반환하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        invalid_plan = VALID_PLAN_DICT.copy()
        del invalid_plan["work_order_id"] # 필수 필드 제거
        mock_call_llm.return_value = json.dumps(invalid_plan)
        agent = ArchitectAgent(DUMMY_CONFIG)

        # 2. 실행 (Act)
        result = agent.run(DUMMY_V_GEN, DUMMY_EXPERT_REPORTS, DUMMY_UNIT_TEST_SUITE)

        # 3. 검증 (Assert)
        assert result is None
        captured = capsys.readouterr()
        assert "LLM 응답 검증에 실패했습니다" in captured.out
        assert "Field required" in captured.out # Pydantic ValidationError 메시지 확인