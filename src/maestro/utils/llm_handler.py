import os
import json
from typing import List, Dict, Any, Optional

# --- 모듈 레벨 변수 ---
_llm_provider: Optional[str] = None
_api_key: Optional[str] = None
_client = None
_mock_call_counter: int = 0 # <-- 호출 카운터


def set_llm_provider(config: Dict[str, Any]):
    """
    main_controller에서 호출되어, 사용할 LLM 공급자와 API 키를 설정합니다.
    """
    global _llm_provider, _api_key, _client, _mock_call_counter
    _mock_call_counter = 0 # <-- 💡 중요: 컨트롤러가 초기화될 때마다 카운터 리셋

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
        # (Anthropic 로직 ... 생략)
        pass

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
            # (OpenAI 로직 ... 생략)
            model = llm_config.get("model", "gpt-5")
            response = _client.chat.completions.create(model=model, messages=messages)
            return response.choices[0].message.content or ""
        
        elif _llm_provider == "anthropic":
            # (Anthropic 로직 ... 생략)
            pass

        # --- 👇 "카운터 기반" Mock 로직 시작 👇 ---
        elif _llm_provider == "mock":
            global _mock_call_counter
            _mock_call_counter += 1

            # --- 💡 1, 2, 3번째 호출은 "전문가" ---
            if _mock_call_counter <= 3:
                # 1단계 전문가용 '보고서(list)' 반환
                mock_role = "MockExpert"
                if _mock_call_counter == 1:
                    mock_role = "PerformanceExpert"
                elif _mock_call_counter == 2:
                    mock_role = "ReadabilityExpert"
                else:
                    mock_role = "SecurityExpert"
                
                fake_report = [
                    {
                        "suggestion_id": f"MOCK-00{_mock_call_counter}",
                        "agent_role": mock_role, 
                        "title": f"Mock suggestion from {mock_role}",
                        "target_code_block": "main.py#L1-L1",
                        "severity": "Low",
                        "reasoning": "This is a mock response for an Expert.",
                        "proposed_change": "pass",
                        "expected_impact": "None. This is a mock.",
                        "potential_tradeoffs": "None."
                    }
                ]
                return json.dumps(fake_report)

            # --- 💡 4번째 호출은 "아키텍트" ---
            elif _mock_call_counter == 4:
                # 2단계 아키텍트용 '계획서(dict)' 반환
                fake_plan = {
                    "work_order_id": "MOCK-WO-001", 
                    "synthesis_goal": "Balance",      
                    "reasoning_log": "This is a mock reasoning log to pass validation.",
                    "instructions": [                 
                        {
                            "step": 1,
                            "action": "REPLACE", 
                            "description": "Mock step 1: Extract function (to pass validation).",
                            "target_code_block": "main.py#L1-L1",
                            "details": {
                                "refactor_type": "EXTRACT_FUNCTION", 
                                "new_function_name": "mock_extracted_function",
                                "new_function_body": "def mock_extracted_function():\n    pass # Mock body"
                            },
                            "source_suggestion_ids": ["MOCK-001", "MOCK-002", "MOCK-003"],
                            "rationale": "Mock rationale based on principles."
                        }
                    ]
                }
                return json.dumps(fake_plan)
            
            # --- 💡 5번째 호출은 "개발자" ---
            elif _mock_call_counter == 5:
                # 💡💡💡 [수정] 01:30 로그의 2개 에러를 잡기 위해 업그레이드! 💡💡💡
                fake_dev_output = {
                    "status": "SUCCESS", # <-- [수정] "MOCK_SUCCESS" -> "SUCCESS"
                    "final_code": "# This is mock code from the developer",
                    "log": ["Mock Developer Agent ran successfully."] # <-- [수정] str -> list
                }
                return json.dumps(fake_dev_output)

            # --- 💡 그 외 (자기 회고 등) ---
            else:
                return '{"status": "mock_fallback_loop", "log": "Mock loop detected."}'
        # --- 👆 Mock 로직 끝 👆 ---

        return ""

    except Exception as e:
        print(f"LLM API 호출 중 심각한 오류 발생: {e}")
        raise