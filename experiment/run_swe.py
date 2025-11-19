import argparse
import yaml
import os
import sys
import datetime

# 프로젝트 루트 경로를 path에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

# [수정] 통합된 MainController 사용
from maestro.core.main_controller import MainController

def load_config(config_path: str):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"설정 로드 실패: {e}")
        exit(1)

def main():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    default_output_dir = f"results/swe_outputs/run_{timestamp}"

    parser = argparse.ArgumentParser(description="MAESTRO SWE-bench Experiment")
    parser.add_argument("--config", type=str, default="config.yml", help="Config file path")

    parser.add_argument("--output_dir", type=str, default=default_output_dir, help="Output directory")
    parser.add_argument("--limit", type=int, default=1, help="Number of issues to process")
    
    args = parser.parse_args()

    print(f" 실험 결과는 다음 폴더에 저장됩니다: {args.output_dir}")
    
    # 설정 로드
    config = load_config(args.config)
    
    # [수정] MainController 초기화
    controller = MainController(config)
    
    # [수정] SWE-bench 전용 워크플로우 실행
    controller.run_swe_workflow(output_base_dir=args.output_dir, limit=args.limit)

if __name__ == "__main__":
    main()