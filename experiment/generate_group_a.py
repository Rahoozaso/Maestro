import os
import argparse
import yaml
import sys
import re

# 프로젝트 루트 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from maestro.utils.llm_handler import set_llm_provider, call_llm
from maestro.utils.file_io import read_text_file, write_text_file

def load_config(config_path: str):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def extract_python_code(text: str) -> str:
    """마크다운 코드 블록 제거"""
    match = re.search(r"```python\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text

def main():
    parser = argparse.ArgumentParser(description="Generate Group A Baseline Code (v_gen)")
    parser.add_argument("--config", type=str, default="config.yml")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=49)
    args = parser.parse_args()

    config = load_config(args.config)
    set_llm_provider(config["llm"])

    base_dir = "data/benchmark/HumanEval"
    
    print(f"===== Group A (Baseline) 생성 시작: Task {args.start} ~ {args.end} =====")

    for i in range(args.start, args.end + 1):
        task_dir = os.path.join(base_dir, str(i))
        prompt_path = os.path.join(task_dir, "prompt.txt")
        output_path = os.path.join(task_dir, "v_gen.py")

        if not os.path.exists(prompt_path):
            print(f"[Skip] {prompt_path} not found.")
            continue

        problem_description = read_text_file(prompt_path)
        
        # Group A 프롬프트: "그냥 기능적으로 동작하게만 짜줘" (Baseline 역할)
        messages = [
            {
                "role": "system", 
                "content": (
                    "You are an advanced AI code generation system acting as a 'Product Manager' and 'Engineer' combination, "
                    "similar to MetaGPT. Your goal is to generate functional Python code based on the user's requirement. "
                    "Focus on correctness and functionality (passing tests) as the highest priority. "
                    "Do not over-optimize for non-functional requirements (like extreme optimization or strict security) "
                    "unless explicitly asked. Just produce standard, working code."
                )
            },
            {
                "role": "user", 
                "content": f"Please provide the complete Python code for the following problem.\nCRITICAL: You MUST keep the original docstring at the top of the function.\n\n{problem_description}"
            }
        ]

        print(f"[{i}] Generating baseline code...")
        try:
            response = call_llm(messages, config["llm"])
            code = extract_python_code(response)
            
            # 결과 저장 (v_gen.py)
            write_text_file(output_path, code)
            print(f"    -> Saved to {output_path}")
            
        except Exception as e:
            print(f"    -> Error: {e}")

    print("===== Group A 생성 완료 =====")

if __name__ == "__main__":
    main()