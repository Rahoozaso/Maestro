import os
from typing import List, Dict, Any, Optional

# --- 모듈 레벨 변수 ---
# 이 변수들은 set_llm_provider를 통해 설정되며, call_llm에서 사용됩니다.
_llm_provider: Optional[str] = None
_api_key: Optional[str] = None
_client = None


def set_llm_provider(config: Dict[str, Any]):
    """
    main_controller에서 호출되어, 사용할 LLM 공급자와 API 키를 설정합니다.
    환경 변수에서 API 키를 불러옵니다.
    """
    global _llm_provider, _api_key, _client

    provider = config.get("provider")
    if not provider:
        raise ValueError(
            "LLM 설정(config.yml)에 'provider'가 지정되지 않았습니다 (e.g., openai, anthropic)."
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
        # 테스트용 모의(Mock) 클라이언트
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
        # set_llm_provider가 먼저 호출되지 않은 경우를 대비한 안전장치
        print(
            "LLM 공급자가 설정되지 않아, llm_config를 사용하여 초기 설정을 시도합니다."
        )
        set_llm_provider(llm_config)

    print(f"'{_llm_provider}' API에 요청을 보냅니다...")

    try:
        if _llm_provider == "openai":
            model = llm_config.get("model", "gpt-4-turbo")
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

        elif _llm_provider == "mock":
            return (
                '{"status": "mock success", "final_code": "pass", "log": ["mock log"]}'
            )

        # 이 부분은 실행되지 않아야 합니다.
        return ""

    except Exception as e:
        print(f"LLM API 호출 중 심각한 오류 발생: {e}")
        # 예외를 다시 발생시켜 상위 호출자가 에러를 인지하고 처리하도록 합니다.
        raise
