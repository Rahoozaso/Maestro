import os
import argparse
import yaml
from typing import Dict, Any

# 💡 '본체'와 동일한 부품(LLM 핸들러, 파일 I/O)을 재활용합니다.
# 이 import가 성공하려면, __init__.py 파일과 PYTHONPATH가 필수입니다.
from maestro.utils.llm_handler import set_llm_provider, call_llm
from maestro.utils.file_io import read_text_file, write_text_file

def load_config(config_path: str) -> Dict[str, Any]:
    """YAML 설정 파일을 로드합니다."""
    # (main_controller.py에서 복사해 온 헬퍼 함수)
    print(f"INFO (Group B): '{config_path}'에서 설정 파일을 로드합니다...")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        print("INFO (Group B): 설정 로드 완료.")
        return config
    except FileNotFoundError:
        print(f"[오류] 설정 파일 '{config_path}'를 찾을 수 없습니다.")
        exit(1)

def main():
    """
    Group B (단일 LLM 개선) 워크플로우를 실행합니다.
    (연구 계획서 5.2.2 기반)
    """
    parser = argparse.ArgumentParser(description="Group B: Simple LLM Enhancement (RQ2)")
    
    parser.add_argument("--config", type=str, required=True, help="설정 파일 (config.yml) 경로")
    parser.add_argument("--input_code", type=str, required=True, help="입력 소스 코드 파일 (v_gen) 경로")
    parser.add_argument("--output_dir", type=str, required=True, help="결과를 저장할 디렉토리")

    args = parser.parse_args()
    print(f"INFO (Group B): 워크플로우 시작. 출력 폴더: {args.output_dir}")

    # 1. 설정 및 LLM 로드
    config = load_config(args.config)
    
    # 💡 '본체'와 동일하게 LLM 공급자를 설정합니다.
    # (config.yml이 'mock'이면, 'llm_handler.py'의 _mock_call_counter가 0으로 리셋됩니다.)
    set_llm_provider(config["llm"])

    # 2. 입력 코드 읽기
    try:
        v_gen_code = read_text_file(args.input_code)
        print(f"INFO (Group B): 입력 코드 '{args.input_code}' 로드 완료.")
    except FileNotFoundError:
        print(f"[오류] 입력 코드 '{args.input_code}'를 찾을 수 없습니다.")
        exit(1)

    # 3. 💡 "단일 프롬프트" 생성 (계획서 5.2.2 기반)
    simple_prompt = f"""
당신은 코드 품질 개선 전문가입니다.
아래 코드를 입력받아, 성능, 가독성, 보안 등 비기능적 요구사항(NFR)을 종합적으로 고려하여 개선해 주십시오.
개선된 코드 블록만 반환해 주십시오.

[입력 코드]
```python
{v_gen_code}
"""
    
    messages = [
        {"role": "user", "content": simple_prompt}
    ]

    # 4. 💡 '원샷'으로 LLM 호출
    print("INFO (Group B): 'mock' API (호출 #1)에 요청을 보냅니다...")
    try:
        # 💡 llm_handler.py의 '호출 카운터'가 1이 됩니다.
        llm_response_str = call_llm(messages, config["llm"])
        
        # --- (예상되는 다음 버그) ---
        # 지금 'mock' 모드라면, 카운터 1번이라서 '전문가'용 가짜 보고서(list)가 반환될 겁니다.
        # Group B는 '개선된 코드(str)'를 기대할 텐데 말이죠.
        # 일단은 Pydantic 검증 없이 원본 응답을 그대로 저장해서 확인부터 해봅시다.
        # ---
        
        print("INFO (Group B): LLM 응답 수신 완료.")

        # 5. 결과 저장 (Pydantic 검증 없음)
        os.makedirs(args.output_dir, exist_ok=True)
        output_path = os.path.join(args.output_dir, "v_final_group_b.py")
        
        # (TODO: 실제로는 LLM 응답에서 ```python ... ``` 코드 블록만 파싱해야 함)
        write_text_file(output_path, llm_response_str)
        
        print(f"INFO (Group B): 결과 저장 완료: {output_path}")

    except Exception as e:
        print(f"[오류] Group B 실행 중 에러 발생: {e}")

    print("===== Group B 워크플로우 종료 =====")


if __name__ == "__main__":
    main()