import json
from pydantic import ValidationError
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from maestro.core.data_models import DeveloperAgentOutput
from maestro.utils.llm_handler import call_llm
from maestro.utils.file_io import read_text_file


class DeveloperAgent(BaseAgent):
    """
    아키텍트의 실행 계획을 바탕으로 LLM을 호출하여 코드를 수정하고,
    그 결과물을 검증하는 개발자 에이전트.
    """

    def run(
        self, v_gen: str, integrated_execution_plan: Dict[str, Any]
    ) -> Optional[DeveloperAgentOutput]:
        """
        개발자 에이전트의 메인 실행 로직입니다.

        Args:
            v_gen (str): 수정 대상이 되는 원본 코드.
            integrated_execution_plan (Dict[str, Any]): 아키텍트가 생성한 실행 계획.

        Returns:
            Optional[DeveloperAgentOutput]: 실행 성공 시 결과 데이터 모델, 실패 시 None.
        """
        print("개발자 에이전트 실행 중...")

        # 1. 프롬프트 로드 및 생성
        prompt_path = (
            self.config["paths"]["prompt_template_dir"] + "developer_prompt.md"
        )
        try:
            prompt_template = read_text_file(prompt_path)
        except FileNotFoundError:
            return None

        # 실행 계획(dict)을 프롬프트에 삽입하기 위해 JSON 문자열로 변환
        plan_str = integrated_execution_plan.model_dump_json(indent=2)
        prompt = prompt_template.format(v_gen=v_gen, integrated_execution_plan=plan_str)

        messages = [
            {
                "role": "system",
                "content": "You are a precise instruction-following expert engine for code modification.",
            },
            {"role": "user", "content": prompt},
        ]

        # 2. LLM 호출
        try:
            response_str = call_llm(messages, self.config["llm"])
            print("LLM 응답을 수신했습니다.")
        except Exception as e:
            print(f"에러: LLM API 호출에 실패했습니다: {e}")
            return None

        # 3. 결과 파싱 및 데이터 모델 검증
        try:
            # LLM 응답에서 JSON 코드 블록만 추출
            json_block = self._extract_json_from_response(response_str)
            parsed_data = json.loads(json_block)

            # Pydantic 모델로 검증
            validated_output = DeveloperAgentOutput.model_validate(parsed_data)
            print(
                f"개발자 에이전트 실행 결과 검증 완료 (상태: {validated_output.status})"
            )
            return validated_output
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            print(f"에러: LLM 응답 검증에 실패했습니다: {e}")
            print(f"LLM 원본 응답:\n---\n{response_str}\n---")
            return None

    def _extract_json_from_response(self, response: str) -> str:
        """응답 문자열에서 JSON 코드 블록을 추출합니다."""
        try:
            # ```json ... ``` 패턴을 찾습니다.
            start_index = response.index("```json") + len("```json")
            end_index = response.rindex("```")
            return response[start_index:end_index].strip()
        except ValueError:
            # 코드 블록이 없는 경우, 전체 문자열을 JSON으로 간주
            print(
                "경고: JSON 코드 블록 마커를 찾을 수 없습니다. 전체 응답을 파싱합니다."
            )
            return response
