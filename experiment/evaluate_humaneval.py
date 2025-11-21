import os
import sys
import pandas as pd
import subprocess
import ast
import glob
from typing import List, Dict

def get_function_name(code: str) -> str:
    """
    생성된 코드에서 정의된 메인 함수 이름을 AST로 추출합니다.
    (HumanEval은 보통 파일 내에 하나의 메인 함수가 있습니다)
    """
    try:
        tree = ast.parse(code)
        # 파일 내의 모든 함수 정의를 찾음
        funcs = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        # 보통 마지막에 정의된 함수가 메인 함수일 가능성이 높거나, 
        # HumanEval 특성상 솔루션 함수가 하나만 잇는 경우가 많음.
        # 여기서는 가장 먼저 발견된 최상위 함수를 가정하거나, 리스트를 반환.
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                return node.name
    except:
        pass
    return None

def evaluate_code(code_path: str, test_path: str) -> str:
    """
    코드와 테스트를 결합하여 실행하고 결과를 반환합니다.
    Returns: "PASS", "FAIL", "ERROR"
    """
    if not os.path.exists(code_path):
        return "MISSING"

    try:
        with open(code_path, "r", encoding="utf-8") as f:
            code_content = f.read()
        with open(test_path, "r", encoding="utf-8") as f:
            test_content = f.read()
            
        # [중요] 테스트 실행 스크립트 조립
        # HumanEval의 test.py는 보통 'def check(candidate): ...' 형태입니다.
        # 따라서 'check(함수명)'을 호출하는 코드를 뒤에 붙여줘야 합니다.
        
        func_name = get_function_name(code_content)
        if not func_name:
            return "ERROR (No Function Found)"

        # 실행할 전체 스크립트 생성
        # 1. 생성된 코드 (Imports + Function)
        # 2. 테스트 코드 (def check...)
        # 3. 실행 트리거 (check(func_name))
        full_script = f"{code_content}\n\n{test_content}\n\nif __name__ == '__main__':\n    check({func_name})"
        
        # 서브프로세스로 실행 (타임아웃 5초)
        result = subprocess.run(
            [sys.executable, "-c", full_script],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return "PASS"
        else:
            # print(f"실패 로그 ({code_path}):\n{result.stderr}") # 디버깅용
            return "FAIL"
            
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR ({str(e)})"

def main():
    base_dir = "results/outputs/HumanEval"
    benchmark_dir = "data/benchmark/HumanEval"
    
    results = []
    
    # 0번부터 49번까지 순회
    for task_id in range(50):
        task_path = os.path.join(base_dir, str(task_id))
        test_path = os.path.join(benchmark_dir, str(task_id), "test.py")
        
        if not os.path.exists(task_path):
            continue
            
        print(f"Evaluating Task {task_id}...")
        
        # 각 그룹별 평가
        row = {"Task ID": task_id}
        
        # Group A (v_gen.py는 benchmark 폴더에 있음)
        group_a_path = os.path.join(benchmark_dir, str(task_id), "v_gen.py")
        row["Group A"] = evaluate_code(group_a_path, test_path)
        
        # Group B, C, D, E (final_code.py는 results 폴더에 있음)
        for group in ["B", "C", "D", "E"]:
            code_path = os.path.join(task_path, group, "final_code.py")
            row[f"Group {group}"] = evaluate_code(code_path, test_path)
            
        results.append(row)

    # 결과 저장
    df = pd.DataFrame(results)
    df.to_csv("humaneval_results.csv", index=False)
    
    print("\n===== 평가 완료 =====")
    print(df)
    print(f"결과 파일 저장됨: humaneval_results.csv")
    
    # 간단한 통계 출력
    print("\n[Pass Rate Summary]")
    for col in df.columns:
        if col == "Task ID": continue
        pass_count = df[col].value_counts().get("PASS", 0)
        print(f"{col}: {pass_count}/50 ({pass_count*2}%)")

if __name__ == "__main__":
    main()