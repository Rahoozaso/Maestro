import json
from pydantic import ValidationError
from typing import List, Optional

# 시스템의 다른 모듈들을 import 합니다.
from .base_agent import BaseAgent
from maestro.core.data_models import ExpertReviewReport, IntegratedExecutionPlan
from maestro.utils.llm_handler import call_llm

class ArchitectAgent(BaseAgent):
    """
    여러 전문가의 리뷰 리포트를 종합하여, NFR 상충 관계를 해결하고
    최종 '통합 실행 계획'을 수립하는 의사결정 에이전트입니다.
    """

    def _extract_json_from_response(self, response_str: str) -> str:
        """
        LLM 응답에서 JSON 코드 블록을 추출합니다.
        응답이 코드 블록(` ```json ... ``` `)을 포함하거나, 순수 JSON 문자열일 수 있습니다.
        """
        if "```json" in response_str:
            # 코드 블록이 있는 경우, 그 안의 내용만 추출
            start = response_str.find("```json") + len("```json")
            end = response_str.rfind("```")
            json_str = response_str[start:end].strip()
            return json_str
        else:
            # 코드 블록이 없는 경우, 전체 문자열을 그대로 반환
            return response_str

    def run(
        self,
        v_gen: str,
        expert_reports: List[ExpertReviewReport],
        unit_test_suite: str,
        synthesis_goal: str = "Balance"
    ) -> Optional[IntegratedExecutionPlan]:
        """
        아키텍트 에이전트의 메인 실행 로직입니다.

        Args:
            v_gen (str): 분석 및 수정 대상이 되는 원본 코드.
            expert_reports (List[ExpertReviewReport]): 전문가 에이전트들의 리뷰 리포트 리스트.
            unit_test_suite (str): 기능 보존 검증을 위한 단위 테스트 코드.
            synthesis_goal (str): 이번 의사결정의 최우선 목표 (e.g., "Balance").

        Returns:
            Optional[IntegratedExecutionPlan]: 성공 시 검증된 실행 계획 객체, 실패 시 None.
        """
        print("아키텍트 에이전트 실행...")

        # 1. 프롬프트 로드 및 생성
        prompt_path = self.config['paths']['prompt_template_dir'] + "architect_prompt.md"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        except FileNotFoundError:
            print(f"오류: 아키텍트 프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
            return None

        # 전문가 리포트 리스트를 JSON 문자열로 직렬화합니다.
        reports_json_str = json.dumps(
            [report.model_dump() for report in expert_reports],
            indent=2,
            ensure_ascii=False
        )

        prompt = prompt_template.format(
            v_gen=v_gen,
            expert_reports=reports_json_str,
            unit_test_suite=unit_test_suite,
            synthesis_goal=synthesis_goal
        )

        messages = [
            {"role": "system", "content": "You are a world-class AI Software Architect, skilled in resolving conflicts and creating strategic refactoring plans."},
            {"role": "user", "content": prompt}
        ]

        # 2. LLM 호출
        try:
            response_str = call_llm(messages, self.config['llm'])
            print("LLM으로부터 통합 실행 계획 초안을 수신했습니다.")
        except Exception as e:
            print(f"LLM API 호출 중 오류 발생: {e}")
            return None

        # 3. 결과 파싱 및 데이터 모델 검증
        try:
            # LLM 응답에서 순수 JSON 문자열만 추출합니다.
            json_str = self._extract_json_from_response(response_str)
            
            # JSON 문자열을 Python 딕셔너리로 파싱합니다.
            parsed_data = json.loads(json_str)
            
            # Pydantic 모델을 사용하여 데이터 구조와 타입을 검증합니다.
            validated_plan = IntegratedExecutionPlan.model_validate(parsed_data)
            
            print(f"통합 실행 계획 검증 완료: Work Order ID '{validated_plan.work_order_id}'")
            return validated_plan
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"LLM 응답 검증에 실패했습니다: {e}")
            print(f"LLM 원본 응답:\n---\n{response_str}\n---")
            return None
