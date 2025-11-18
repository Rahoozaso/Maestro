import os
import argparse
import yaml
import re
from typing import Dict, Any

# '본체'와 동일한 부품(LLM 핸들러, 파일 I/O)을 재활용합니다.
from maestro.utils.llm_handler import set_llm_provider, call_llm
from maestro.utils.file_io import read_text_file, write_text_file

def load_config(config_path: str):
    """YAML 설정 파일을 로드합니다 (독립형)."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"[오류] 설정 파일 로드 실패: {e}")
        exit(1)

def _extract_python_code(response_str: str) -> str:
    """
    LLM 응답에서 Markdown Python 코드 블록(```python ... ```)을 추출합니다.
    태그가 없으면 원본을 반환합니다.
    """
    response_str = response_str.strip()
    
    # 1. ```python ... ``` 블록 찾기
    match = re.search(r"```python\s*\n(.*?)\n\s*```", response_str, re.DOTALL)
    if match:
        return match.group(1).strip()
        
    # 2. ``` ... ``` (태그명 없는) 블록 찾기
    match = re.search(r"```\s*\n(.*?)\n\s*```", response_str, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 3. 블록이 없으면, 원본 문자열 자체가 코드라고 가정
    return response_str

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
    
    # '본체'와 동일하게 LLM 공급자를 설정합니다.
    set_llm_provider(config["llm"])

    # 2. 입력 코드 읽기
    try:
        v_gen_code = read_text_file(args.input_code)
        print(f"INFO (Group B): 입력 코드 '{args.input_code}' 로드 완료.")
    except FileNotFoundError:
        print(f"[오류] 입력 코드 '{args.input_code}'를 찾을 수 없습니다.")
        exit(1)

    # 3. "단일 프롬프트" 생성 (계획서 5.2.2 기반)
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

    # 4. '원샷'으로 LLM 호출
    print(f"INFO (Group B): '{config['llm']['provider']}' API에 요청을 보냅니다...")
    try:
        llm_response_str = call_llm(messages, config["llm"])
        print("INFO (Group B): LLM 응답 수신 완료.")

        # [중요] 코드 블록만 깔끔하게 추출
        final_code = _extract_python_code(llm_response_str)

        # 5. 결과 저장
        os.makedirs(args.output_dir, exist_ok=True)
        output_path = os.path.join(args.output_dir, "v_final_group_b.py")

        # [수정됨] save_file 대신 write_text_file 사용, 원본 덮어쓰기 로직 제거
        write_text_file(output_path, final_code)
        
        print(f"INFO (Group B): 결과 저장 완료: {output_path}")

    except Exception as e:
        print(f"[오류] Group B 실행 중 에러 발생: {e}")

    print("===== Group B 워크플로우 종료 =====")


if __name__ == "__main__":
    main()