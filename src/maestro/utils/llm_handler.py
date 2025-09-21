import os
from openai import OpenAI

def call_llm(messages: list, llm_config: dict) -> str:

    # 1. Conda 환경 변수에서 API 키를 직접 로드합니다.
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY 환경 변수가 설정되지 않았습니다. "
            "'conda env config vars set' 명령어로 설정해주세요."
        )

    # 2. 전달받은 llm_config에서 나머지 설정을 가져옵니다.
    model_name = llm_config["model"]
    provider = llm_config["provider"]
    parameters = llm_config["parameters"]
    
    # 3. API를 호출합니다.
    if provider == "openai":
        client = OpenAI(api_key=api_key, timeout=parameters["timeout"])
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=parameters["temperature"],
            max_tokens=parameters["max_tokens"]
        )
        return response.choices[0].message.content or ""
    else:
        # 다른 LLM 제공자를 위한 로직 (향후 확장 가능)
        raise NotImplementedError(f"{provider} 제공자는 아직 구현되지 않았습니다.")
