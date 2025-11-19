import json
import re
from pydantic import ValidationError
from typing import List
from .base_agent import BaseAgent
from maestro.core.data_models import ExpertReviewReport
from maestro.utils.llm_handler import call_llm
from maestro.utils.file_io import read_text_file


def _extract_json_from_response(response_str: str) -> str:
    """LLM 응답에서 Markdown JSON 코드 블록 추출"""
    response_str = response_str.strip()
    match = re.search(r"```(json)?\s*\n(.*?)\n\s*```", response_str, re.DOTALL)
    if match:
        return match.group(2).strip()
    return response_str


class PerformanceExpert(BaseAgent):
    def run(self, code_to_analyze: str, unit_tests: str) -> List[ExpertReviewReport]:
        print("성능 전문가 에이전트 실행 (Live Mode)...")
        prompt_path = self.config["paths"]["prompt_template_dir"] + "performance_prompt.md"
        try:
            prompt_template = read_text_file(prompt_path)
        except FileNotFoundError:
            return []

        prompt = prompt_template.format(v_gen=code_to_analyze, unit_test_suite=unit_tests)
        messages = [
            {
                "role": "system", 
                "content": "You are a hyper-critical Performance Optimization Expert. You do not settle for 'good enough'."
            },
            {
                "role": "system", 
                "content": """CRITICAL INSTRUCTION: You MUST find potential improvements.
                - If the code uses recursion, suggest iteration to avoid stack overflow.
                - If it uses lists where sets would be faster, flag it.
                - If imports are not lazy or specific, flag it.
                - Even micro-optimizations are required if no major issues exist.
                DO NOT return an empty list."""
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response_str = call_llm(messages, self.config["llm"])
            print("LLM 응답 수신 완료.")
        except Exception:
            return []

        try:
            json_str = _extract_json_from_response(response_str)
            if not json_str: return []
            parsed_data = json.loads(json_str)
            validated_reports = [ExpertReviewReport.model_validate(item) for item in parsed_data]
            print(f"{len(validated_reports)}개의 성능 개선 제안 검증 완료.")
            return validated_reports
        except (json.JSONDecodeError, ValidationError):
            return []


class ReadabilityExpert(BaseAgent):
    def run(self, code_to_analyze: str, unit_tests: str) -> List[ExpertReviewReport]:
        print("가독성 전문가 에이전트 실행 (Live Mode)...")
        prompt_path = self.config["paths"]["prompt_template_dir"] + "readability_prompt.md"
        try:
            prompt_template = read_text_file(prompt_path)
        except FileNotFoundError:
            return []

        prompt = prompt_template.format(v_gen=code_to_analyze, unit_test_suite=unit_tests)
        messages = [
            {
                "role": "system", 
                "content": "You are a pedantic Python Code Quality Expert who obsesses over PEP8 and clean code."
            },
            {
                "role": "system", 
                "content": """CRITICAL INSTRUCTION: You MUST find issues.
                - Flag usage of 'typing.Any' and demand specific types.
                - Flag short variable names (e.g., 'ml', 'ol') and demand descriptive names.
                - Flag missing docstrings or comments.
                - Flag complex list comprehensions.
                DO NOT return an empty list."""
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response_str = call_llm(messages, self.config["llm"])
            print("LLM 응답 수신 완료.")
        except Exception:
            return []

        try:
            json_str = _extract_json_from_response(response_str)
            if not json_str: return []
            parsed_data = json.loads(json_str)
            validated_reports = [ExpertReviewReport.model_validate(item) for item in parsed_data]
            print(f"{len(validated_reports)}개의 가독성 개선 제안 검증 완료.")
            return validated_reports
        except (json.JSONDecodeError, ValidationError):
            return []


class SecurityExpert(BaseAgent):
    def run(self, code_to_analyze: str, unit_tests: str) -> List[ExpertReviewReport]:
        print("보안 전문가 에이전트 실행")
        prompt_path = self.config["paths"]["prompt_template_dir"] + "security_prompt.md"
        try:
            prompt_template = read_text_file(prompt_path)
        except FileNotFoundError:
            return []

        prompt = prompt_template.format(v_gen=code_to_analyze, unit_test_suite=unit_tests)
        messages = [
            {
                "role": "system", 
                "content": "You are a paranoid Security Expert. You assume all code is vulnerable."
            },
            {
                "role": "system", 
                "content": """CRITICAL INSTRUCTION: You MUST find potential risks.
                - Flag missing input validation or type checks.
                - Flag recursion depth risks (DoS).
                - Flag unsafe imports.
                - Suggest defensive assertions.
                DO NOT return an empty list unless the code is trivial."""
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response_str = call_llm(messages, self.config["llm"])
            print("LLM 응답 수신 완료.")
        except Exception:
            return []

        try:
            json_str = _extract_json_from_response(response_str)
            if not json_str: return []
            parsed_data = json.loads(json_str)
            validated_reports = [ExpertReviewReport.model_validate(item) for item in parsed_data]
            print(f"{len(validated_reports)}개의 보안 개선 제안 검증 완료.")
            return validated_reports
        except (json.JSONDecodeError, ValidationError):
            return []