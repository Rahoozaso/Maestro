from pydantic import BaseModel, Field, DiscriminatedUnion
from typing import List, Literal, Optional, Union

class ExpertReviewReport(BaseModel):
    """전문가 에이전트가 생성하는 단일 개선 제안 리포트 모델"""
    suggestion_id: str = Field(description="제안의 고유 ID (e.g., PERF-001)")
    agent_role: Literal["PerformanceExpert", "ReadabilityExpert", "SecurityExpert"]
    title: str = Field(description="한 줄 요약")
    target_code_block: str = Field(description="수정 대상 코드 위치 (e.g., file.py#L10-L15)")
    severity: Literal["Critical", "High", "Medium", "Low"]
    reasoning: str = Field(description="왜 수정이 필요한지에 대한 논리적 근거")
    proposed_change: str = Field(description="제안하는 코드 수정안")

# 각 리팩토링 커맨드별 인자(Arguments) 모델 -
class ExtractFunctionArgs(BaseModel):
    """'함수 추출' 커맨드에 필요한 인자 모델"""
    refactor_type: Literal["EXTRACT_FUNCTION"]
    new_function_name: str
    new_function_body: str

class RenameVariableArgs(BaseModel):
    """'변수명 변경' 커맨드에 필요한 인자 모델"""
    refactor_type: Literal["RENAME_VARIABLE"]
    scope: str = Field(description="변수명의 유효 범위 (e.g., 함수 이름, 전역)")
    old_name: str
    new_name: str

#모든 인자 모델을 하나로 묶는 Union 
RefactorArguments = DiscriminatedUnion(
    union=[ExtractFunctionArgs, RenameVariableArgs],
    discriminator="refactor_type"
)


class InstructionStep(BaseModel):
    """개발자가 수행할 단일 작업 지시 모델"""
    step: int = Field(description="실행 순서 (1부터 시작)")
    description: str = Field(description="수행할 작업에 대한 자연어 설명")
    action: Literal["REPLACE", "ADD", "DELETE", "REFACTOR_AND_MODIFY"]
    target_code_block: str
    
    # 단순한 코드 변경을 위한 필드
    new_code: Optional[str] = Field(None, description="REPLACE 또는 ADD 액션에 사용될 새로운 코드")
    
    # 복잡한 리팩토링 커맨드를 위한 필드
    details: Optional[RefactorArguments] = Field(None, discriminator="refactor_type")
    
    # 메타 정보
    source_suggestion_ids: List[str]
    rationale: str

class IntegratedExecutionPlan(BaseModel):
    """Architect 에이전트의 최종 산출물인 '통합 실행 계획' 모델"""
    work_order_id: str
    synthesis_goal: Literal["Balance", "Security_Focus", "Performance_Focus"]
    instructions: List[InstructionStep]
