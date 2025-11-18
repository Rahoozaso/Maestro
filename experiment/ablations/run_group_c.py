import argparse
import yaml
from typing import Dict, Any

# 이 import가 성공하려면 'PYTHONPATH=./src'가 필수입니다.
from maestro.utils.llm_handler import set_llm_provider
from maestro.core.main_controller import MainController

def load_config(config_path: str):
    """YAML 설정 파일을 로드합니다 (독립형)."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"[오류] 설정 파일 로드 실패: {e}")
        exit(1)

def main():
    """
    Group C (Ablation: MAESTRO w/o Architect) 워크플로우를 실행합니다.
    (연구 계획서 5.2.2 기반)
    --architect_mode="RuleBased"로 고정됩니다.
    """
    parser = argparse.ArgumentParser(description="Group C: RuleBased MAESTRO (RQ3)")
    
    #  '본체'와 달리 --architect_mode 인수가 빠졌습니다. (고정값이므로)
    parser.add_argument("--config", type=str, required=True, help="설정 파일 (config.yml) 경로")
    parser.add_argument("--input_code", type=str, required=True, help="입력 소스 코드 파일 (v_gen) 경로")
    parser.add_argument("--unit_tests", type=str, required=True, help="유닛 테스트 파일 경로")
    parser.add_argument("--output_dir", type=str, required=True, help="결과를 저장할 디렉토리")

    args = parser.parse_args()
    print(f"INFO (Group C): 워크플로우 시작. [RuleBased Mode]. 출력 폴더: {args.output_dir}")

    # 1. 설정 및 LLM 로드
    config = load_config(args.config)
    set_llm_provider(config["llm"]) #  카운터 리셋!

    # 2. 컨트롤러 초기화
    controller = MainController(config)
    
    # 3. 워크플로우 실행
    print("INFO (Group C): MainController 워크플로우를 시작합니다...")
    try:
        controller.run_workflow(
            source_code_path=args.input_code,
            unit_test_path=args.unit_tests,
            output_dir=args.output_dir,
            architect_mode="RuleBased", # <--  Group C의 핵심: '규칙 기반' 고정
            enable_retrospection=True   # (RuleBased는 어차피 회고를 안 하지만, 기본값 유지)
        )
    except Exception as e:
        print(f"[오류] Group C 실행 중 에러 발생: {e}")
        
    print("===== Group C 워크플로우 종료 =====")

if __name__ == "__main__":
    main()