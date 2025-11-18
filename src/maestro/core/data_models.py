from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Union, Dict, Any


class ExpertReviewReport(BaseModel):
    """전문가 에이전트가 생성하는 단일 개선 제안 리포트 모델"""

    suggestion_id: str = Field(description="제안의 고유 ID (e.g., PERF-001)")
    agent_role: Literal["PerformanceExpert", "ReadabilityExpert", "SecurityExpert"]
    title: str = Field(description="한 줄 요약")
    target_code_block: str = Field(
        description="수정 대상 코드 위치 (e.g., file.py#L10-L15)"
    )
    severity: Literal["Critical", "High", "Medium", "Low"]
    reasoning: str = Field(description="왜 수정이 필요한지에 대한 논리적 근거")
    proposed_change: str = Field(description="제안하는 코드 수정안")


class InstructionStep(BaseModel):
    """개발자가 수행할 단일 작업 지시 모델"""

    step: int = Field(description="실행 순서 (1부터 시작)")
    description: str = Field(description="수행할 작업에 대한 자연어 설명")
    
    # 💡 [핵심 수정] Literal 제한을 풀고 str(문자열)로 변경하여 모든 Action 허용
    action: str = Field(
        description="수행할 작업 유형 (e.g., REPLACE, ADD_TEST_FILE, MODIFY_LOGIC, etc.)"
    )
    
    target_code_block: str

    # 단순한 코드 변경을 위한 필드
    new_code: Optional[str] = Field(
        None, description="REPLACE, ADD 액션 등에 사용될 새로운 코드"
    )

    # 💡 [핵심 수정] 복잡한 Union 검증을 제거하고, 임의의 딕셔너리를 허용 (Crash 방지)
    details: Optional[Dict[str, Any]] = Field(
        None, description="리팩토링에 필요한 추가 상세 정보 (구조 자유)"
    )

    # 메타 정보
    source_suggestion_ids: List[str]
    rationale: str


class IntegratedExecutionPlan(BaseModel):
    """Architect 에이전트의 최종 산출물인 '통합 실행 계획' 모델"""

    work_order_id: str
    
    # 💡 [핵심 수정] Literal 제한 해제 ('Resolve Issue' 등 허용)
    synthesis_goal: str = Field(
        description="이번 의사결정의 목표 (e.g., Balance, Resolve Issue)"
    )
    
    reasoning_log: str 
    instructions: List[InstructionStep]


class DeveloperAgentOutput(BaseModel):
    """Developer 에이전트의 최종 출력 스키마를 정의하는 모델"""

    status: Literal["SUCCESS", "PARTIAL_SUCCESS", "FAILURE"] = Field(
        description="작업 실행 상태"
    )
    final_code: str = Field(description="모든 지시가 적용된 최종 코드")
    log: List[str] = Field(description="각 단계별 실행 성공/실패 기록")