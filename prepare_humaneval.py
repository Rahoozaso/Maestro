import json
import os
import re # task_id에서 숫자만 추출하기 위해 추가

# 입력/출력 경로 설정
INPUT_JSONL_PATH = "HumanEval.jsonl"
OUTPUT_BASE_DIR = "data/benchmark/HumanEval"

def extract_task_number(task_id: str) -> str:
    """'HumanEval/0' 같은 task_id에서 숫자만 추출합니다."""
    match = re.search(r'\d+$', task_id)
    return match.group(0) if match else task_id # 숫자를 못 찾으면 원본 ID 사용

def main():
    print(f"'{INPUT_JSONL_PATH}' 파일을 읽어 HumanEval 데이터를 준비합니다...")

    if not os.path.exists(INPUT_JSONL_PATH):
        print(f"[오류] 입력 파일 '{INPUT_JSONL_PATH}'을 찾을 수 없습니다.")
        print("1단계: 데이터셋 다운로드 스크립트를 먼저 실행하세요.")
        return

    # 출력 기본 디렉토리 생성
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
        
    processed_count = 0
    try:
        with open(INPUT_JSONL_PATH, "r", encoding="utf-8") as infile:
            for line in infile:
                try:
                    data = json.loads(line.strip())

                    task_id_full = data.get("task_id")
                    prompt = data.get("prompt")
                    test_code = data.get("test")
                    # canonical_solution = data.get("canonical_solution") # 필요 시 사용

                    if not task_id_full or not prompt or not test_code:
                        print(f"[경고] 필요한 필드가 누락된 라인을 건너<0xEB><0x9A><0x81>니다: {line.strip()[:50]}...")
                        continue

                    # task_id에서 숫자 부분 추출 (예: 'HumanEval/0' -> '0')
                    task_num_str = extract_task_number(task_id_full)
                        
                    # 해당 문제 번호의 폴더 경로 생성
                    problem_dir = os.path.join(OUTPUT_BASE_DIR, task_num_str)
                    os.makedirs(problem_dir, exist_ok=True)

                    # test.py 파일 저장
                    test_filepath = os.path.join(problem_dir, "test.py")
                    with open(test_filepath, "w", encoding="utf-8") as f_test:
                        # HumanEval의 테스트 코드는 보통 바로 실행 가능한 형태
                        # 필요에 따라 import 구문 등을 추가해야 할 수 있음
                        f_test.write(test_code)
                        # 테스트 실행을 위한 기본 진입점 추가 (선택 사항)
                        # f_test.write("\n\n# Example of how to run tests if needed")
                        # f_test.write("\n# check()")

                    # prompt.txt 파일 저장 (Group A 입력용)
                    prompt_filepath = os.path.join(problem_dir, "prompt.txt")
                    with open(prompt_filepath, "w", encoding="utf-8") as f_prompt:
                        f_prompt.write(prompt)

                    processed_count += 1

                except json.JSONDecodeError:
                    print(f"[경고] JSON 파싱 오류 발생 라인을 건너<0xEB><0x9A><0x81>니다: {line.strip()[:50]}...")
                except Exception as e:
                    print(f"[경고] 문제 {task_id_full} 처리 중 예상치 못한 오류 발생: {e}")


        print(f"총 {processed_count}개의 HumanEval 문제가 성공적으로 처리되었습니다.")
        print(f"데이터는 '{OUTPUT_BASE_DIR}' 폴더 아래 각 번호별 하위 폴더에 저장되었습니다.")

    except Exception as e:
        print(f"데이터 처리 중 심각한 오류 발생: {e}")

if __name__ == "__main__":
    main()
