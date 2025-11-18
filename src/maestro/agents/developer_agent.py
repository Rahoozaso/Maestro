import json
import re  
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
            # [수정 1] 더 강력한 JSON 추출 로직 사용 (Regex)
            json_block = self._extract_json_from_response(response_str)
            
            # [방어] 빈 응답 처리
            if not json_block:
                 print("에러: LLM이 유효한 JSON을 반환하지 않았습니다.")
                 return None

            parsed_data = json.loads(json_block)

            # Pydantic 모델로 검증
            validated_output = DeveloperAgentOutput.model_validate(parsed_data)
            
            # [수정 2] JSON 내부 'final_code' 필드에 있는 ```python 마커 제거
            if validated_output.final_code:
                validated_output.final_code = self._clean_markdown_code_fences(validated_output.final_code)

            print(
                f"개발자 에이전트 실행 결과 검증 완료 (상태: {validated_output.status})"
            )
            return validated_output
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            print(f"에러: LLM 응답 검증에 실패했습니다: {e}")
            print(f"LLM 원본 응답:\n---\n{response_str}\n---")
            return None

    def _extract_json_from_response(self, response: str) -> str:
        """
        응답 문자열에서 JSON 코드 블록을 추출합니다.
        (```json ... ```) 또는 (``` ... ```) 또는 (raw JSON)을 모두 처리합니다.
        """
        response = response.strip()
        
        # 1. ```json ... ``` 또는 ``` ... ``` 블록 찾기
        # group(2)가 실제 내용이 됩니다.
        match = re.search(r"```(json)?\s*\n(.*?)\n\s*```", response, re.DOTALL)
        if match:
            return match.group(2).strip() 

        # 2. 블록이 없으면, 원본 문자열 자체가 유효한 JSON일 수 있다고 가정
        return response

    def _clean_markdown_code_fences(self, code_str: str) -> str:
        """
        코드 문자열 내부에 포함된 Markdown 코드 펜스(```python ... ```)를 제거합니다.
        LLM이 JSON 필드 값 안에 코드를 넣을 때 가끔 마크다운 문법을 포함시키는 경우를 방어합니다.
        """
        code_str = code_str.strip()
        # 문자열 전체가 ``` ... ``` 로 감싸져 있는지 확인 (python 옵션 포함)
        match = re.search(r"^```(?:python)?\s*\n(.*?)\n\s*```$", code_str, re.DOTALL)
        if match:
            return match.group(1).strip()
        return code_str