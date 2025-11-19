from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Union, Dict, Any

class ExpertReviewReport(BaseModel):
    """전문가 에이전트 리포트"""
    suggestion_id: str = Field(description="제안 ID")
    agent_role: str  # Literal 제한 해제
    title: str
    target_code_block: str
    severity: str    # Literal 제한 해제
    reasoning: str
    proposed_change: str

class InstructionStep(BaseModel):
    """작업 지시 모델 (매우 유연함)"""
    step: int
    description: str
    
    # 1. Action 제한 해제
    action: str = Field(description="수행할 작업 유형")
    
    target_code_block: str
    new_code: Optional[str] = None

    # 2. Details 완전 자유화 (검증 안 함)
    # 어떤 키-값 쌍이 들어와도 다 받아줍니다.
    details: Optional[Dict[str, Any]] = None 

    source_suggestion_ids: List[str]
    rationale: str

class IntegratedExecutionPlan(BaseModel):
    """통합 실행 계획"""
    work_order_id: str
    # 3. Goal 제한 해제
    synthesis_goal: str 
    # 4. Log 필드 필수 아님 (Optional) - Group C 오류 방지
    reasoning_log: Optional[str] = "" 
    instructions: List[InstructionStep]

class DeveloperAgentOutput(BaseModel):
    """개발자 출력"""
    status: str # Literal 제한 해제
    final_code: str
    log: List[str]