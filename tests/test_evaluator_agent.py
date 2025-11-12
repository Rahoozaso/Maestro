# tests/test_evaluator_agent.py

import pytest

# 테스트 대상 클래스를 임포트합니다.
from maestro.agents.evaluator_agent import EvaluatorAgent, EvaluationResult

# --- 테스트 케이스 정의 ---

# 각 튜플은 (테스트 이름, 입력 데이터, 예상 점수, 예상 결정) 형식입니다.
test_cases = [
    (
        "excellent_case_success",
        {  # 입력 데이터
            "security": {"highest_severity": "None"},  # 40점
            "readability": {"cyclomatic_complexity": 5},  # 30점
            "performance": {"improvement_percentage": 20.0},  # 30점
        },
        {  # 예상 점수
            "security": 40,
            "readability": 30,
            "performance": 30,
            "total": 100,
        },
        "HIGH_QUALITY_SUCCESS",  # 예상 결정
    ),
    (
        "exactly_85_success",
        {
            "security": {"highest_severity": "None"},  # 40점
            "readability": {"cyclomatic_complexity": 11},  # 15점
            "performance": {"improvement_percentage": 15.0},  # 30점
        },
        {"security": 40, "readability": 15, "performance": 30, "total": 85},
        "HIGH_QUALITY_SUCCESS",
    ),
    (
        "borderline_fail_by_one_point",
        {
            "security": {"highest_severity": "None"},  # 40점
            "readability": {"cyclomatic_complexity": 11},  # 15점
            "performance": {"improvement_percentage": 14.9},  # 15점
        },
        {"security": 40, "readability": 15, "performance": 15, "total": 70},
        "FINAL_FAILURE",
    ),
    (
        "security_veto_case_fail",
        {  # 다른 점수가 만점이더라도, 보안 점수가 0점이면 무조건 실패
            "security": {"highest_severity": "High"},
            "readability": {"cyclomatic_complexity": 1},
            "performance": {"improvement_percentage": 100.0},
        },
        {"security": 0, "readability": 30, "performance": 30, "total": 60},
        "FINAL_FAILURE",
    ),
    (
        "all_terrible_case_fail",
        {
            "security": {"highest_severity": "High"},
            "readability": {"cyclomatic_complexity": 25},
            "performance": {"improvement_percentage": -10.0},
        },
        {"security": 0, "readability": 0, "performance": 0, "total": 0},
        "FINAL_FAILURE",
    ),
]


@pytest.mark.parametrize(
    "test_name, report_data, expected_scores, expected_decision", test_cases
)
def test_evaluator_agent(test_name, report_data, expected_scores, expected_decision):
    """
    다양한 시나리오에 대해 EvaluatorAgent의 점수 계산과 최종 결정 로직을 검증합니다.
    """
    # 1. 준비 (Arrange)
    agent = EvaluatorAgent(config={})  # 이 에이전트는 config가 필요 없습니다.

    # 2. 실행 (Act)
    result = agent.run(report_data)

    # 3. 검증 (Assert)
    assert isinstance(result, EvaluationResult)
    assert result.scores.model_dump() == expected_scores
    assert result.decision == expected_decision
