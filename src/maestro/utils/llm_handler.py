import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI, AuthenticationError

# --- [Global Token Tracker] ---
TOTAL_TOKENS = {"prompt": 0, "completion": 0}

def reset_token_usage():
    global TOTAL_TOKENS
    TOTAL_TOKENS = {"prompt": 0, "completion": 0}

def get_token_usage() -> Dict[str, int]:
    return TOTAL_TOKENS
# ------------------------------

# --- 모듈 레벨 변수 ---
_llm_provider: Optional[str] = None
_api_key: Optional[str] = None
_client = None
_model_name = "gpt-4o" 
_temperature = 0.7

def set_llm_provider(config: Dict[str, Any]):
    global _llm_provider, _api_key, _client, _model_name, _temperature

    provider = config.get("provider", "openai")
    _llm_provider = provider
    _model_name = config.get("model", "gpt-4o")
    _temperature = config.get("parameters", {}).get("temperature", 0.7)

    if _llm_provider == "openai":
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("OpenAI를 사용하려면 'pip install openai'를 실행해주세요.")
        
        _api_key = os.getenv("OPENAI_API_KEY")
        if not _api_key:
            raise ValueError("'OPENAI_API_KEY' 환경 변수가 설정되지 않았습니다.")
        _client = OpenAI(api_key=_api_key)
        print(f"LLM 공급자가 'openai'로 설정되었습니다. (Model: {_model_name})")

    elif _llm_provider == "anthropic":
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("Anthropic을 사용하려면 'pip install anthropic'를 실행해주세요.")

        _api_key = os.getenv("ANTHROPIC_API_KEY")
        if not _api_key:
            raise ValueError("'ANTHROPIC_API_KEY' 환경 변수가 설정되지 않았습니다.")
        _client = Anthropic(api_key=_api_key)
        print(f"LLM 공급자가 'anthropic'로 설정되었습니다. (Model: {_model_name})")

    elif _llm_provider == "mock":
        _client = "mock"
        print("LLM 공급자가 'mock'으로 설정되었습니다. 실제 API 호출은 이루어지지 않습니다.")
    else:
        raise ValueError(f"지원되지 않는 LLM 공급자입니다: {_llm_provider}")


def call_llm(messages: List[Dict[str, str]], llm_config: Dict[str, Any] = None) -> str:
    global _client, TOTAL_TOKENS

    if _client is None:
        if llm_config:
            set_llm_provider(llm_config)
        else:
            set_llm_provider({"provider": "openai"})

    print(f"'{_llm_provider}' API에 요청을 보냅니다... (Model: {_model_name})")

    try:
        if _llm_provider == "openai":
            # 최신 모델(o1, gpt-5 등) 대응
            is_new_model = "o1" in _model_name or "gpt-5" in _model_name
            
            params = {
                "model": _model_name,
                "messages": messages,
            }
            
            # 💡 [수정] GPT-5/o1 모델은 temperature 설정을 지원하지 않거나 고정값이므로 제외
            if not is_new_model:
                params["temperature"] = _temperature

            if is_new_model:
                params["max_completion_tokens"] = 4096
            else:
                params["max_tokens"] = 4096

            response = _client.chat.completions.create(**params)
            
            if response.usage:
                TOTAL_TOKENS["prompt"] += response.usage.prompt_tokens
                TOTAL_TOKENS["completion"] += response.usage.completion_tokens
                
            return response.choices[0].message.content.strip()
        
        elif _llm_provider == "anthropic":
            system_prompt = ""
            user_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    user_messages.append(msg)

            response = _client.messages.create(
                model=_model_name,
                system=system_prompt,
                max_tokens=4096,
                messages=user_messages,
                temperature=_temperature
            )
            
            if hasattr(response, 'usage'):
                 TOTAL_TOKENS["prompt"] += response.usage.input_tokens
                 TOTAL_TOKENS["completion"] += response.usage.output_tokens

            return response.content[0].text

        elif _llm_provider == "mock":
            return "Mock response: This is a simulated reply from the AI."

        return ""

    except AuthenticationError:
        raise ValueError("API 인증 실패. API 키를 확인하세요.")
    except Exception as e:
        print(f"LLM 호출 중 오류 발생: {e}")
        raise