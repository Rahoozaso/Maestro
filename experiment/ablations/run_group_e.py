import argparse
import yaml
from typing import Dict, Any

#  '본체'의 핵심 부품(MainController)과 헬퍼 함수를 import합니다.
from maestro.core.main_controller import MainController, load_config
from maestro.utils.llm_handler import set_llm_provider

def main():
    """
    Group E (Ablation: MAESTRO w/o Retrospection) 워크플로우를 실행합니다.
    (연구 계획서 5.2.2 기반)
    --architect_mode="CoT"로 고정되고, --enable_retrospection=False로 고정됩니다.
    """
    parser = argparse.ArgumentParser(description="Group E: MAESTRO w/o Retrospection")
    
    parser.add_argument("--config", type=str, required=True, help="설정 파일 (config.yml) 경로")
    parser.add_argument("--input_code", type=str, required=True, help="입력 소스 코드 파일 (v_gen) 경로")
    parser.add_argument("--unit_tests", type=str, required=True, help="유닛 테스트 파일 경로")
    parser.add_argument("--output_dir", type=str, required=True, help="결과를 저장할 디렉토리")

    args = parser.parse_args()
    print(f"INFO (Group E): 워크플로우 시작. [CoT Mode / No Retrospection]. 출력 폴더: {args.output_dir}")

    # 1. 설정 및 LLM 로드
    config = load_config(args.config)
    set_llm_provider(config["llm"]) #  카운터 리셋! (아, 이젠 '프롬프트 엿보기'죠. 좋습니다)

    # 2. 컨트롤러 초기화
    controller = MainController(config)
    
    # 3. 워크플로우 실행
    print("INFO (Group E): MainController 워크플로우를 시작합니다...")
    try:
        controller.run_workflow(
            source_code_path=args.input_code,
            unit_test_path=args.unit_tests,
            output_dir=args.output_dir,
            architect_mode="CoT",              # <--  Group E는 'CoT' 모드
            enable_retrospection=False      # <--  Group E의 핵심: '자기 회고' 끔
        )
    except Exception as e:
        print(f"[오류] Group E 실행 중 에러 발생: {e}")
        
    print("===== Group E 워크플로우 종료 =====")

if __name__ == "__main__":
    main()