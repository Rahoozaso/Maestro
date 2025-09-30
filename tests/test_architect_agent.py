import json
import pytest
from unittest.mock import patch

# Pydantic 모델과 테스트 대상 에이전트 클래스를 임포트합니다.
from maestro.core.data_models import ExpertReviewReport, IntegratedExecutionPlan, InstructionStep
from maestro.agents.architect_agent import ArchitectAgent

# --- 테스트를 위한 기본 데이터 ---

# 모든 테스트에서 사용할 임시 설정값입니다.
DUMMY_CONFIG = {
    "llm": {"provider": "mock"},
    "paths": {"prompt_template_dir": "data/prompt/"}
}

# 에이전트에게 전달할 임시 데이터입니다.
DUMMY_CODE = "def old_function():\n    pass"
DUMMY_UNIT_TESTS = "assert True"

# 테스트에서 사용할 가짜(mock) 전문가 리뷰 리포트입니다.
MOCK_EXPERT_REPORTS = [
    ExpertReviewReport(
        suggestion_id="PERF-001",
        agent_role="PerformanceExpert",
        title="Use set for lookup",
        target_code_block="main.py#L1-L5",
        severity="High",
        reasoning="...",
        proposed_change="..."
    ),
    ExpertReviewReport(
        suggestion_id="SEC-CRITICAL-001",
        agent_role="SecurityExpert",
        title="SQL Injection",
        target_code_block="main.py#L10-L12",
        severity="Critical",
        reasoning="...",
        proposed_change="..."
    )
]

# LLM이 성공적으로 반환했다고 가정하는 유효한 '통합 실행 계획' 딕셔너리입니다.
VALID_PLAN_DICT = {
    "work_order_id": "WO-TEST-123",
    "synthesis_goal": "Balance",
    "instructions": [
        {
            "step": 1,
            "description": "Fix critical security issue.",
            "action": "REPLACE",
            "target_code_block": "main.py#L10-L12",
            "new_code": "cursor.execute(?, (param,))",
            "source_suggestion_ids": ["SEC-CRITICAL-001"],
            "rationale": "Security Primacy Principle."
        }
    ]
}

# --- 아키텍트 에이전트 테스트 클래스 ---

class TestArchitectAgent:
    """
    ArchitectAgent의 핵심 로직을 테스트합니다.
    """

    # --- 성공 케이스 ---

    @patch('maestro.agents.architect_agent.read_text_file')
    @patch('maestro.agents.architect_agent.call_llm')
    def test_run_success(self, mock_call_llm, mock_read_file):
        """
        [성공] 모든 과정이 정상적으로 진행될 때, 유효한 IntegratedExecutionPlan 객체를 반환하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        mock_read_file.return_value = "Prompt template content"
        mock_call_llm.return_value = json.dumps(VALID_PLAN_DICT)
        agent = ArchitectAgent(DUMMY_CONFIG)

        # 2. 실행 (Act)
        plan = agent.run(DUMMY_CODE, MOCK_EXPERT_REPORTS, DUMMY_UNIT_TESTS)

        # 3. 검증 (Assert)
        mock_read_file.assert_called_once()
        mock_call_llm.assert_called_once()
        
        assert isinstance(plan, IntegratedExecutionPlan)
        assert plan.work_order_id == "WO-TEST-123"
        assert len(plan.instructions) == 1
        assert isinstance(plan.instructions[0], InstructionStep)
        assert plan.instructions[0].step == 1

    @patch('maestro.agents.architect_agent.read_text_file')
    @patch('maestro.agents.architect_agent.call_llm')
    def test_run_success_with_json_wrapper(self, mock_call_llm, mock_read_file):
        """
        [성공] LLM 응답이 JSON 코드 블록으로 감싸져 있어도 정상적으로 파싱하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        mock_read_file.return_value = "Prompt template"
        wrapped_response = f"```json\n{json.dumps(VALID_PLAN_DICT)}\n```"
        mock_call_llm.return_value = wrapped_response
        agent = ArchitectAgent(DUMMY_CONFIG)

        # 2. 실행 (Act)
        plan = agent.run(DUMMY_CODE, MOCK_EXPERT_REPORTS, DUMMY_UNIT_TESTS)

        # 3. 검증 (Assert)
        assert isinstance(plan, IntegratedExecutionPlan)
        assert plan.work_order_id == "WO-TEST-123"

    # --- 실패 케이스 ---

    @patch('maestro.agents.architect_agent.read_text_file')
    def test_run_prompt_file_not_found(self, mock_read_file, capsys):
        """
        [실패] 프롬프트 파일을 찾지 못했을 때 None을 반환하고 에러를 출력하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        mock_read_file.side_effect = FileNotFoundError
        agent = ArchitectAgent(DUMMY_CONFIG)

        # 2. 실행 (Act)
        plan = agent.run(DUMMY_CODE, MOCK_EXPERT_REPORTS, DUMMY_UNIT_TESTS)

        # 3. 검증 (Assert)
        assert plan is None
        captured = capsys.readouterr()
        assert "프롬프트 파일을 찾을 수 없습니다" in captured.out

    @patch('maestro.agents.architect_agent.read_text_file')
    @patch('maestro.agents.architect_agent.call_llm')
    def test_run_llm_returns_invalid_json(self, mock_call_llm, mock_read_file, capsys):
        """
        [실패] LLM이 유효하지 않은 JSON을 반환했을 때 None을 반환하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        mock_read_file.return_value = "Prompt template"
        mock_call_llm.return_value = '{"key": "value", "malformed'
        agent = ArchitectAgent(DUMMY_CONFIG)

        # 2. 실행 (Act)
        plan = agent.run(DUMMY_CODE, MOCK_EXPERT_REPORTS, DUMMY_UNIT_TESTS)
        
        # 3. 검증 (Assert)
        assert plan is None
        captured = capsys.readouterr()
        assert "LLM 응답 검증에 실패했습니다" in captured.out

    @patch('maestro.agents.architect_agent.read_text_file')
    @patch('maestro.agents.architect_agent.call_llm')
    def test_run_llm_returns_invalid_schema(self, mock_call_llm, mock_read_file, capsys):
        """
        [실패] LLM이 Pydantic 모델과 맞지 않는 스키마의 JSON을 반환했을 때 None을 반환하는지 테스트합니다.
        """
        # 1. 준비 (Arrange)
        mock_read_file.return_value = "Prompt template"
        invalid_schema_plan = {"synthesis_goal": "Balance", "instructions": []} # work_order_id 누락
        mock_call_llm.return_value = json.dumps(invalid_schema_plan)
        agent = ArchitectAgent(DUMMY_CONFIG)

        # 2. 실행 (Act)
        plan = agent.run(DUMMY_CODE, MOCK_EXPERT_REPORTS, DUMMY_UNIT_TESTS)

        # 3. 검증 (Assert)
        assert plan is None
        captured = capsys.readouterr()
        assert "LLM 응답 검증에 실패했습니다" in captured.out
