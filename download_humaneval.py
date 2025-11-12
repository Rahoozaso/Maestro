from datasets import load_dataset
import json

# Hugging Face Hub에서 HumanEval 데이터셋 로드
dataset = load_dataset("openai_humaneval")

# 'test' 스플릿의 데이터를 jsonl 파일로 저장
output_filepath = "HumanEval.jsonl"
with open(output_filepath, "w", encoding="utf-8") as f:
    for example in dataset['test']:
        # 각 예제를 JSON 문자열로 변환하여 파일에 쓰기
        json_string = json.dumps(example, ensure_ascii=False)
        f.write(json_string + "\n")

print(f"HumanEval 데이터셋이 '{output_filepath}' 파일로 저장되었습니다.")