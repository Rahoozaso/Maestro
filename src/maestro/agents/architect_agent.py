import json
import re  # 정규표현식 import
from pydantic import ValidationError
from typing import List, Optional
from typing import Dict
import datetime

# 시스템의 다른 모듈들을 import 합니다.
from .base_agent import BaseAgent
from maestro.core.data_models import (
    ExpertReviewReport,
    IntegratedExecutionPlan,
    InstructionStep,
)
from maestro.utils.llm_handler import call_llm
from maestro.utils.file_io import read_text_file


class ArchitectAgent(BaseAgent):
    """
    여러 전문가의 리뷰 리포트를 종합하여, NFR 상충 관계를 해결하고
    최종 '통합 실행 계획'을 수립하는 의사결정 에이전트입니다.
    """

    def _extract_json_from_response(self, response_str: str) -> str:
        """
        LLM 응답에서 Markdown JSON 코드 블록을 추출합니다.
        """
        response_str = response_str.strip()
        
        # 1. (```json ... ```) 또는 (``` ... ```) 블록 찾기
        match = re.search(r"```(json)?\s*\n(.*?)\n\s*```", response_str, re.DOTALL)
        if match:
            return match.group(2).strip() 

        # 2. 블록이 없으면, 원본 문자열 자체가 유효한 JSON일 수 있다고 가정
        return response_str

    def run(
        self,
        v_gen: str,
        expert_reports: List[ExpertReviewReport],
        unit_test_suite: str,
        synthesis_goal: str = "Balance",
        architect_mode: str = "CoT",
        failure_feedback: Optional[str] = None,
        previous_plan: Optional[IntegratedExecutionPlan] = None,
    ) -> Optional[IntegratedExecutionPlan]:
        """
        아키텍트 에이전트의 메인 실행 로직입니다.
        """
        print("아키텍트 에이전트 실행...")

        if architect_mode == "RuleBased":
            return self._run_rule_based(
                v_gen, expert_reports, unit_test_suite, synthesis_goal
            )
        else:
            return self._run_cot_based(
                v_gen,
                expert_reports,
                unit_test_suite,
                synthesis_goal,
                failure_feedback,
                previous_plan,
            )

    # --- 규칙 기반 실행 메소드 ---
    def _run_rule_based(
        self,
        v_gen: str,
        expert_reports: List[ExpertReviewReport],
        unit_test_suite: str, 
        synthesis_goal: str,
    ) -> Optional[IntegratedExecutionPlan]:
        """
        간단한 규칙(Severity 우선)에 따라 통합 실행 계획을 생성합니다.
        """
        print("규칙 기반 아키텍트 로직 실행 중...")
        instructions: List[InstructionStep] = []
        step_counter = 1
        processed_suggestion_ids = set()

        # Severity를 숫자로 변환하는 맵 (높을수록 우선)
        severity_map = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}

        # 1. Critical 보안 제안 최우선 처리
        critical_security_reports = [
            r for r in expert_reports
            if r.agent_role == "SecurityExpert" and r.severity == "Critical"
        ]
        for report in sorted(critical_security_reports, key=lambda r: r.suggestion_id):
            if report.suggestion_id not in processed_suggestion_ids:
                instructions.append(
                    InstructionStep(
                        step=step_counter,
                        description=f"[규칙 기반] {report.suggestion_id}: {report.title}",
                        action="REPLACE", # 단순화
                        target_code_block=report.target_code_block,
                        new_code=report.proposed_change,
                        source_suggestion_ids=[report.suggestion_id],
                        rationale="Rule-based: Critical security issue prioritized.",
                    )
                )
                processed_suggestion_ids.add(report.suggestion_id)
                step_counter += 1

        # 2. 나머지 제안 중 동일 블록 경합 처리: Severity가 가장 높은 제안 선택
        remaining_reports = [
            r for r in expert_reports if r.suggestion_id not in processed_suggestion_ids
        ]
        grouped_reports: Dict[str, List[ExpertReviewReport]] = {}
        for report in remaining_reports:
            if report.target_code_block:
                if report.target_code_block not in grouped_reports:
                    grouped_reports[report.target_code_block] = []
                grouped_reports[report.target_code_block].append(report)

        selected_reports_after_conflict: List[ExpertReviewReport] = []
        for block, reports_in_group in grouped_reports.items():
            best_report = max(
                reports_in_group,
                key=lambda r: (
                    severity_map.get(r.severity, 0),
                    -ord(r.suggestion_id[0]),
                    r.suggestion_id,
                ),
            )
            selected_reports_after_conflict.append(best_report)

        # 3. 선택된 제안들을 Severity 내림차순 정렬
        final_selected_reports = sorted(
            selected_reports_after_conflict,
            key=lambda r: (severity_map.get(r.severity, 0), r.suggestion_id),
            reverse=True,
        )
        for report in final_selected_reports:
            if report.suggestion_id not in processed_suggestion_ids:
                instructions.append(
                    InstructionStep(
                        step=step_counter,
                        description=f"[규칙 기반] {report.suggestion_id}: {report.title}",
                        action="REPLACE",
                        target_code_block=report.target_code_block,
                        new_code=report.proposed_change,
                        source_suggestion_ids=[report.suggestion_id],
                        rationale=f"Rule-based: Highest severity ({report.severity}) suggestion selected.",
                    )
                )
                processed_suggestion_ids.add(report.suggestion_id)
                step_counter += 1

        if not instructions:
            print("규칙 기반 아키텍트: 적용할 유효한 개선안이 없습니다.")
            return None

        # 최종 계획 생성 (여기가 수정된 부분입니다)
        plan = IntegratedExecutionPlan(
            work_order_id=f"WO-RuleBased-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            synthesis_goal=synthesis_goal,
            reasoning_log="[Rule-Based Logic] Generated automatically by sorting suggestions based on Severity.",
            instructions=instructions
        )
        print(f"규칙 기반 통합 실행 계획 생성 완료: {len(instructions)}개 작업")
        return plan

    def _run_cot_based(
        self,
        v_gen: str,
        expert_reports: List[ExpertReviewReport],
        unit_test_suite: str,
        synthesis_goal: str = "Balance",
        failure_feedback: Optional[str] = None, 
        previous_plan: Optional[IntegratedExecutionPlan] = None,
    ) -> Optional[IntegratedExecutionPlan]:
        """
        CoT 추론을 사용하여 통합 실행 계획을 생성합니다.
        """
        print("CoT 기반 아키텍트 로직 실행 중...")
        prompt_path = (
            self.config["paths"]["prompt_template_dir"] + "architect_prompt.md"
        )
        try:
            prompt_template = read_text_file(prompt_path)
        except FileNotFoundError:
            print(f"오류: 아키텍트 프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
            return None

        reports_json_str = json.dumps(
            [report.model_dump() for report in expert_reports],
            indent=2,
            ensure_ascii=False,
        )

        feedback_section = ""
        if failure_feedback:
            feedback_section += f"\n\n# PREVIOUS ATTEMPT FEEDBACK\n{failure_feedback}"

        try:
            prompt = prompt_template.format(
                v_gen=v_gen,
                expert_reports=reports_json_str,
                unit_test_suite=unit_test_suite,
                synthesis_goal=synthesis_goal,
                failure_feedback_section=feedback_section,
            )
        except KeyError as e:
            print(f"오류: 아키텍트 프롬프트 템플릿 포맷팅 실패. 누락된 키: {e}")
            return None

        messages = [
            {
                "role": "system",
                "content": "You are a world-class AI Software Architect, skilled in resolving conflicts and creating strategic refactoring plans using Chain of Thought reasoning.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response_str = call_llm(messages, self.config["llm"])
            print("LLM으로부터 통합 실행 계획 초안을 수신했습니다.")
        except Exception as e:
            print(f"LLM API 호출 중 오류 발생: {e}")
            return None

        try:
            json_str = self._extract_json_from_response(response_str)
            if not json_str:
                print(f"LLM 응답 검증 실패: 응답이 비어있습니다.")
                return None
            
            parsed_data = json.loads(json_str)
            validated_plan = IntegratedExecutionPlan.model_validate(parsed_data)

            print(
                f"통합 실행 계획 검증 완료: Work Order ID '{validated_plan.work_order_id}'"
            )
            return validated_plan
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"LLM 응답 검증 실패: {e}")
            print(f"LLM 원본 응답 (일부):\n{response_str[:500]}...")
            return None