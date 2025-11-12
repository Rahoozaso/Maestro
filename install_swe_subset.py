import json
import os
import subprocess
import sys

# --- (1) 설정: 여기서 숫자와 경로를 수정하세요 ---

# 설치할 문제 개수
NUM_PROBLEMS_TO_INSTALL = 30

# 원본 SWE-bench 저장소 경로 (바탕화면에 클론한 위치)
SWE_BENCH_REPO_PATH = r"C:\Users\amry0\Desktop\SWE-bench"   

# 문제 목록 파일 (lite 버전 사용을 권장)
DATASET_JSON_NAME = "swe-bench-lite.json"

# MAESTRO 프로젝트 내에 문제가 설치될 최종 경로
OUTPUT_PATH = r"./data/benchmark/SWE-bench"

# ---------------------------------------------

def get_task_ids_from_json(json_path, count):
    """JSON 파일에서 처음 'count'개의 instance_id를 읽어옵니다."""
    if not os.path.exists(json_path):
        print(f"[오류] 문제 목록 파일을 찾을 수 없습니다: {json_path}")
        print("SWE-bench 저장소 경로(SWE_BENCH_REPO_PATH)가 올바른지 확인하세요.")
        return None
    
    instance_ids = []
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for i, item in enumerate(data):
            if i >= count:
                break
            if "instance_id" in item:
                instance_ids.append(item["instance_id"])
    
    if len(instance_ids) < count:
        print(f"[경고] 요청한 {count}개보다 적은 {len(instance_ids)}개의 문제 ID만 찾았습니다.")
        
    return instance_ids

def main():
    print(f"SWE-bench 문제 설치를 시작합니다 (총 {NUM_PROBLEMS_TO_INSTALL}개)...")
    
    # 1. 문제 목록 JSON 파일의 전체 경로 구성
    json_path = os.path.join(SWE_BENCH_REPO_PATH, "swebench", "problems", DATASET_JSON_NAME)
    
    # 2. JSON 파일에서 30개의 문제 ID 추출
    task_ids = get_task_ids_from_json(json_path, NUM_PROBLEMS_TO_INSTALL)
    
    if not task_ids:
        print("문제 ID를 추출하지 못해 설치를 중단합니다.")
        return

    print(f"총 {len(task_ids)}개의 문제 ID를 성공적으로 로드했습니다.")
    
    # 3. 설치될 폴더 생성
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    print(f"데이터를 다음 폴더에 설치합니다: {OUTPUT_PATH}")

    # 4. get_tasks 스크립트 실행 명령어 구성
    # python -m swebench.collect.get_tasks --tasks ID1 ID2 ID3 ... --output_path ...
    command = [
        "python",
        "-m", "swebench.collect.get_tasks",
        "--tasks"
    ]
    command.extend(task_ids) # 30개의 ID를 인자로 추가
    command.extend(["--output_path", OUTPUT_PATH])
    
    print("\n[실행될 명령어]")
    # 화면에 보여줄 때는 ID가 너무 길어 생략 처리
    print(f"python -m swebench.collect.get_tasks --tasks {task_ids[0]} ... (총 {len(task_ids)}개) --output_path {OUTPUT_PATH}")
    
    # 5. 스크립트 실행
    print("\n데이터 다운로드 및 설정을 시작합니다... (시간이 걸릴 수 있습니다)")
    try:
        # Popen을 사용하여 실시간 출력을 스트리밍할 수 있으나,
        # 간단한 실행을 위해 subprocess.run을 사용합니다.
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
        print("\n[stdout]")
        print(result.stdout)
        print("\n[stderr]")
        print(result.stderr)
        print(f"\n[성공] {len(task_ids)}개의 문제가 성공적으로 설치되었습니다.")
        
    except subprocess.CalledProcessError as e:
        print("\n[오류] SWE-bench 문제 설치 중 오류가 발생했습니다.")
        print(f"Return Code: {e.returncode}")
        print("[stdout]")
        print(e.stdout)
        print("[stderr]")
        print(e.stderr)
    except FileNotFoundError:
        print("\n[오류] 'python' 명령어를 찾을 수 없습니다.")
        print("SWE-bench 설치 시 사용했던 Conda 환경('swebench_env')이 활성화되었는지 확인하세요.")

if __name__ == "__main__":
    main()