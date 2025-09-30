from typing import Dict, Any, Literal

# Pydantic 모델을 사용하여 입출력 데이터 구조를 명확히 정의합니다.
from pydantic import BaseModel, Field

# 다른 에이전트와의 일관성을 위해 BaseAgent를 상속합니다.
from .base_agent import BaseAgent


# --- 입출력 데이터 모델 정의 ---

class SecurityData(BaseModel):
    """보안 점수 계산에 필요한 입력 데이터 모델"""
    highest_severity: Literal["High", "Medium", "Low", "None"]

class ReadabilityData(BaseModel):
    """가독성 점수 계산에 필요한 입력 데이터 모델"""
    cyclomatic_complexity: int

class PerformanceData(BaseModel):
    """성능 점수 계산에 필요한 입력 데이터 모델"""
    improvement_percentage: float

class QuantitativeDataReport(BaseModel):
    """품질 게이트 에이전트의 전체 입력 데이터 모델"""
    security: SecurityData
    readability: ReadabilityData
    performance: PerformanceData

class Scores(BaseModel):
    """산출된 NFR 점수 모델"""
    security: int
    readability: int
    performance: int
    total: int

class EvaluationResult(BaseModel):
    """품질 게이트 에이전트의 최종 출력 데이터 모델"""
    scores: Scores
    decision: Literal["HIGH_QUALITY_SUCCESS", "FINAL_FAILURE"]
    rationale: str = Field(description="최종 결정에 대한 논리적 근거")


# --- EvaluatorAgent 클래스 ---

class EvaluatorAgent(BaseAgent):
    """
    자동화된 도구의 정량적 데이터를 기반으로 코드 품질을 평가하고,
    사전에 정의된 규칙에 따라 최종 성공/실패를 판정하는 에이전트.
    """

    def _calculate_security_score(self, severity: str) -> int:
        """보안 심각도에 따라 점수를 계산합니다."""
        if severity == "High":
            return 0  # Veto 조건
        if severity == "Medium":
            return 15
        if severity == "Low":
            return 30
        if severity == "None":
            return 40
        return 0

    def _calculate_readability_score(self, complexity: int) -> int:
        """순환 복잡도에 따라 점수를 계산합니다."""
        if 1 <= complexity <= 10:
            return 30
        if 11 <= complexity <= 20:
            return 15
        return 0

    def _calculate_performance_score(self, improvement: float) -> int:
        """성능 개선율에 따라 점수를 계산합니다."""
        if improvement >= 15:
            return 30
        if 5 <= improvement < 15:
            return 15
        if 0 <= improvement < 5:
            return 5
        return 0

    def run(self, quantitative_data_report: Dict[str, Any]) -> EvaluationResult:
        """
        품질 게이트의 메인 실행 로직입니다.

        Args:
            quantitative_data_report (Dict[str, Any]): 정적/동적 분석 도구로부터 수집된 NFR 지표.

        Returns:
            EvaluationResult: 최종 평가 결과(점수, 결정, 근거)를 담은 데이터 객체.
        """
        print("품질 게이트(Evaluator) 에이전트 실행...")

        # 1. 입력 데이터 검증
        try:
            report = QuantitativeDataReport.model_validate(quantitative_data_report)
        except Exception as e:
            # 입력 데이터 형식이 잘못된 경우 처리
            return EvaluationResult(
                scores=Scores(security=0, readability=0, performance=0, total=0),
                decision="FINAL_FAILURE",
                rationale=f"입력 데이터 형식 오류: {e}"
            )

        # 2. 각 NFR 점수 계산
        security_score = self._calculate_security_score(report.security.highest_severity)
        readability_score = self._calculate_readability_score(report.readability.cyclomatic_complexity)
        performance_score = self._calculate_performance_score(report.performance.improvement_percentage)
        total_score = security_score + readability_score + performance_score

        scores = Scores(
            security=security_score,
            readability=readability_score,
            performance=performance_score,
            total=total_score
        )

        # 3. 최종 결정
        decision: Literal["HIGH_QUALITY_SUCCESS", "FINAL_FAILURE"]
        if total_score >= 85 and security_score > 0:
            decision = "HIGH_QUALITY_SUCCESS"
        else:
            decision = "FINAL_FAILURE"

        # 4. 근거(Rationale) 생성
        rationale = (
            f"종합 품질 점수 {total_score}점. "
            f"기준 점수(85점) {'충족' if decision == 'HIGH_QUALITY_SUCCESS' else '미달'}으로 최종 결정. "
            f"세부 점수: 보안 {security_score}/40, "
            f"가독성 {readability_score}/30 (순환 복잡도: {report.readability.cyclomatic_complexity}), "
            f"성능 {performance_score}/30 ({report.performance.improvement_percentage}% 개선)."
        )
        if security_score == 0:
            rationale += " (보안 Veto 조건 발동)"

        print(f"평가 완료: {decision} ({rationale})")

        return EvaluationResult(scores=scores, decision=decision, rationale=rationale)