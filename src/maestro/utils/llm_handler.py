import os
import json
from typing import List, Dict, Any, Optional

# --- 모듈 레벨 변수 ---
_llm_provider: Optional[str] = None
_api_key: Optional[str] = None
_client = None


def set_llm_provider(config: Dict[str, Any]):
    """
    main_controller에서 호출되어, 사용할 LLM 공급자와 API 키를 설정합니다.
    """
    global _llm_provider, _api_key, _client

    provider = config.get("provider")
    if not provider:
        raise ValueError(
            "LLM 설정(config.yml)에 'provider'가 지정되지 않았습니다."
        )

    _llm_provider = provider

    if _llm_provider == "openai":
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI를 사용하려면 'pip install openai'를 실행해주세요."
            )
        _api_key = os.getenv("OPENAI_API_KEY")
        if not _api_key:
            raise ValueError("'OPENAI_API_KEY' 환경 변수가 설정되지 않았습니다.")
        _client = OpenAI(api_key=_api_key)
        print("LLM 공급자가 'openai'로 설정되었습니다.")

    elif _llm_provider == "anthropic":
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "Anthropic을 사용하려면 'pip install anthropic'를 실행해주세요."
            )

        _api_key = os.getenv("ANTHROPIC_API_KEY")
        if not _api_key:
            raise ValueError("'ANTHROPIC_API_KEY' 환경 변수가 설정되지 않았습니다.")
        _client = Anthropic(api_key=_api_key)
        print("LLM 공급자가 'anthropic'로 설정되었습니다.")

    elif _llm_provider == "mock":
        _client = "mock"
        print(
            "LLM 공급자가 'mock'으로 설정되었습니다. 실제 API 호출은 이루어지지 않습니다."
        )
    else:
        raise ValueError(f"지원되지 않는 LLM 공급자입니다: {_llm_provider}")


def call_llm(messages: List[Dict[str, str]], llm_config: Dict[str, Any]) -> str:
    """
    설정된 LLM 공급자를 사용하여 API를 호출하고 응답을 문자열로 반환합니다.
    """
    if _client is None:
        set_llm_provider(llm_config)

    print(f"'{_llm_provider}' API에 요청을 보냅니다...")

    try:
        if _llm_provider == "openai":
            model = llm_config.get("model", "gpt-5")
            response = _client.chat.completions.create(model=model, messages=messages)
            return response.choices[0].message.content or ""
        
        elif _llm_provider == "anthropic":
            model = llm_config.get("model", "claude-3-sonnet-20240229")
            system_prompt = ""
            if messages and messages[0]["role"] == "system":
                system_prompt = messages[0]["content"]
                user_messages = messages[1:]
            else:
                user_messages = messages

            response = _client.messages.create(
                model=model,
                system=system_prompt,
                max_tokens=4096,
                messages=user_messages,
            )
            return response.content[0].text

       # --- "답안지 + 문제지 기반" Mock 로직 (최종판 v4) ---
        elif _llm_provider == "mock":
            
            # 💡 '시스템 프롬프트' (첫 번째 메시지)만 엿봅니다.
            system_prompt_str = ""
            if messages and messages[0]["role"] in ("system", "user"):
                # 'content'가 None일 수 있는 엣지 케이스 방어
                if messages[0].get("content"):
                    system_prompt_str = messages[0].get("content", "").lower()

            # --- (디버깅용 print 구문 제거) ---

            # --- 💡 1순위: Group B (단일 LLM) ---
            if "nfr을 종합적으로" in system_prompt_str or "비기능적 요구사항" in system_prompt_str:
                fake_code = """# This is a mock code response for Group B
        def mock_group_b_function():
            pass"""
                return fake_code # 순수 문자열 반환

            # --- 💡 2순위: 개발자 (Group C, D, E) ---
            # (방금 "심문"으로 알아낸 '진짜' 키워드로 수정!)
            elif "you are a precise instruction-following expert engine for code modification" in system_prompt_str:
                # '답안지(models.py)'의 "DeveloperAgentOutput" 모델을 따름
                fake_dev_output = {
                    "status": "SUCCESS", 
                    "final_code": "# This is mock code from the developer",
                    "log": ["Mock Developer Agent ran successfully."] 
                }
                return json.dumps(fake_dev_output)

            # --- 💡 3순위: 아키텍트 (Group D, E) ---
            # ('진짜' 키워드 적용 완료)
            elif "you are a world-class ai software architect" in system_prompt_str:
                # '답안지(models.py)'의 "IntegratedExecutionPlan" 모델을 따름
                fake_plan = {
                    "work_order_id": "MOCK-WO-001", 
                    "synthesis_goal": "Balance",      
                    "reasoning_log": "This is a mock reasoning log...",
                    "instructions": [                 
                        {
                            "step": 1,
                            "action": "REPLACE",
                            "description": "Mock step 1...",
                            "target_code_block": "main.py#L1-L1",
                            "details": {
                                "refactor_type": "EXTRACT_FUNCTION", 
                                "new_function_name": "mock_extracted_function",
                                "new_function_body": "def mock_extracted_function():\n    pass"
                            },
                            "source_suggestion_ids": ["MOCK-001"],
                            "rationale": "Mock rationale.",
                            "new_code": None
                        }
                    ]
                }
                return json.dumps(fake_plan)
            
            # --- 💡 4순위: 전문가 (Group C, D, E) ---
            # ('진짜' 키워드 적용 완료)
            mock_role = None
            if "you are a world-class expert in python code performance optimization" in system_prompt_str:
                mock_role = "PerformanceExpert"
            elif "you are a world-class expert in python code readability optimization" in system_prompt_str:
                mock_role = "ReadabilityExpert"
            elif "you are a world-class expert in python code security optimization" in system_prompt_str:
                mock_role = "SecurityExpert"

            if mock_role:
                # '답안지(models.py)'의 "ExpertReviewReport" 모델을 따름
                fake_report = [
                    {
                        "suggestion_id": f"MOCK-001-{mock_role}",
                        "agent_role": mock_role, 
                        "title": f"Mock suggestion from {mock_role}",
                        "target_code_block": "main.py#L1-L1",
                        "severity": "Low",
                        "reasoning": "This is a mock response for an Expert.",
                        "proposed_change": "pass"
                    }
                ]
                return json.dumps(fake_report)
            
            # --- 💡 5순위: 예외 처리 (어떤 키워드도 감지되지 않음) ---
            else:
                fallback_response = {
                    "status": "mock_fallback_unknown",
                    "log": "Mock logic failed to identify prompt. No specific mock handler was triggered."
                }
                return json.dumps(fallback_response)
        # --- 👆 Mock 로직 끝 👆 ---

        return ""

    except Exception as e:
        print(f"LLM API 호출 중 심각한 오류 발생: {e}")
        raise