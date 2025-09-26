import json
from pydantic import ValidationError
from typing import List
from .base_agent import BaseAgent
from maestro.core.data_models import ExpertReviewReport
from maestro.utils.llm_handler import call_llm

class PerformanceExpert(BaseAgent):

    def run(self, code_to_analyze: str) -> List[ExpertReviewReport]:
        print("성능 전문가 에이전트 실행 (Live Mode)...")

        # 1. 프롬프트 로드 및 생성
        prompt_path = self.config['paths']['prompt_template_dir'] + "performance_prompt.md"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        except FileNotFoundError:
            print(f"에러: 프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
            return []

        prompt = prompt_template.format(v_gen=code_to_analyze)
        messages = [
            {"role": "system", "content": "You are a world-class expert in Python code performance optimization."},
            {"role": "user", "content": prompt}
        ]

        # 2. LLM 호출 (llm_handler 사용)
        try:
            response_str = call_llm(messages, self.config['llm'])
            print("LLM 응답 수신 완료.")
        except Exception as e:
            print(f"LLM API 호출 중 오류 발생: {e}")
            return []

        # 3. 결과 파싱 및 데이터 모델 검증
        try:
            parsed_data = json.loads(response_str)
            validated_reports = [ExpertReviewReport.model_validate(item) for item in parsed_data]
            print(f"{len(validated_reports)}개의 성능 개선 제안 검증 완료.")
            return validated_reports
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"LLM 응답 검증 실패: {e}")
            print(f"LLM 원본 응답:\n---\n{response_str}\n---")
            return []
        
class ReadabilityExpert(BaseAgent):

    def run(self, code_to_analyze: str) -> List[ExpertReviewReport]:
        print("가독성 전문가 에이전트 실행 (Live Mode)...")

        # 1. 프롬프트 로드 및 생성
        prompt_path = self.config['paths']['prompt_template_dir'] + "readability_prompt.md"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        except FileNotFoundError:
            print(f"에러: 프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
            return []

        prompt = prompt_template.format(v_gen=code_to_analyze)
        messages = [
            {"role": "system", "content": "You are a world-class expert in Python code readability optimization."},
            {"role": "user", "content": prompt}
        ]

        # 2. LLM 호출 (llm_handler 사용)
        try:
            response_str = call_llm(messages, self.config['llm'])
            print("LLM 응답 수신 완료.")
        except Exception as e:
            print(f"LLM API 호출 중 오류 발생: {e}")
            return []

        # 3. 결과 파싱 및 데이터 모델 검증
        try:
            parsed_data = json.loads(response_str)
            validated_reports = [ExpertReviewReport.model_validate(item) for item in parsed_data]
            print(f"{len(validated_reports)}개의 가독성 개선 제안 검증 완료.")
            return validated_reports
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"LLM 응답 검증 실패: {e}")
            print(f"LLM 원본 응답:\n---\n{response_str}\n---")
            return []

class SecurityExpert(BaseAgent):

    def run(self, code_to_analyze: str) -> List[ExpertReviewReport]:
        print("보안 전문가 에이전트 실행")

        # 1. 프롬프트 로드 및 생성
        prompt_path = self.config['paths']['prompt_template_dir'] + "security_prompt.md"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        except FileNotFoundError:
            print(f"에러: 프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
            return []

        prompt = prompt_template.format(v_gen=code_to_analyze)
        messages = [
            {"role": "system", "content": "You are a world-class expert in Python code security optimization."},
            {"role": "user", "content": prompt}
        ]

        # 2. LLM 호출 (llm_handler 사용)
        try:
            response_str = call_llm(messages, self.config['llm'])
            print("LLM 응답 수신 완료.")
        except Exception as e:
            print(f"LLM API 호출 중 오류 발생: {e}")
            return []

        # 3. 결과 파싱 및 데이터 모델 검증
        try:
            parsed_data = json.loads(response_str)
            validated_reports = [ExpertReviewReport.model_validate(item) for item in parsed_data]
            print(f"{len(validated_reports)}개의 보안 개선 제안 검증 완료.")
            return validated_reports
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"LLM 응답 검증 실패: {e}")
            print(f"LLM 원본 응답:\n---\n{response_str}\n---")
            return []
