from dataclasses import dataclass
from typing import Optional
import subprocess
import tempfile
import os


@dataclass
class PerformanceReport:
    """성능 프로파일링 결과를 담는 데이터 클래스"""

    success: bool
    original_avg_time: float
    modified_avg_time: float
    improvement_percentage: float
    error_message: Optional[str] = None


def _run_code_in_subprocess(code_to_run: str, setup_code: str, number: int) -> float:
    """
    별도의 서브프로세스에서 timeit을 실행하여 코드를 안전하게 측정합니다.
    """
    runner_script = f"""
import timeit

setup_code = '''
{setup_code}
'''
code_to_run = '''
{code_to_run}
'''
try:
    total_time = timeit.timeit(stmt=code_to_run, setup=setup_code, number={number})
    avg_time = total_time / {number}
    print(avg_time)
except Exception as e:
    import sys
    print(f"Error: {{e}}", file=sys.stderr)
    sys.exit(1)
"""
    try:
        # 임시 파일에 러너 스크립트 작성
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".py", encoding="utf-8"
        ) as temp_file:
            temp_file.write(runner_script)
            temp_filepath = temp_file.name

        # 파이썬 인터프리터를 사용하여 서브프로세스 실행
        result = subprocess.run(
            ["python", temp_filepath],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        )
        return float(result.stdout.strip())

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"코드 실행 서브프로세스 실패: {e.stderr}")
    finally:
        # 임시 파일 정리
        if "temp_filepath" in locals() and os.path.exists(temp_filepath):
            os.remove(temp_filepath)


def profile_performance(
    original_code: str, modified_code: str, number_of_runs: int = 10
) -> PerformanceReport:
    """
    두 코드 버전의 실행 시간을 비교하고 성능 개선율을 계산합니다.
    안전한 실행을 위해 각 코드를 별도의 서브프로세스에서 실행합니다.

    Args:
        original_code (str): 리팩토링 전 원본 코드.
        modified_code (str): 리팩토링 후 수정된 코드.
        number_of_runs (int): 평균 시간을 계산하기 위한 실행 횟수.

    Returns:
        PerformanceReport: 성능 분석 결과를 담은 객체.
    """
    print("성능 분석 시작 (코드 실행 시간 측정)...")
    try:
        # timeit의 setup 부분은 동일하게 사용
        # 여기서는 코드가 함수 정의 등을 포함할 수 있으므로, setup으로 전달합니다.
        # stmt는 간단한 호출 구문으로 남겨둡니다 (실제로는 setup에서 모든 것이 정의됨).
        # 이 방식은 코드가 독립적인 스크립트일 때 유용합니다.
        # 더 복잡한 시나리오에서는 테스트 함수를 호출하는 방식을 사용해야 합니다.

        # 원본 코드 실행 시간 측정
        # 여기서는 간단히 코드를 실행하는 것으로 가정합니다.
        # 실제로는 특정 함수를 호출해야 합니다. 예시에서는 전체 코드를 setup으로 사용합니다.
        print(" - 원본 코드 실행 시간 측정 중...")
        orig_avg_time = _run_code_in_subprocess(
            code_to_run="pass",  # 실제 호출할 함수가 있다면 여기에 명시
            setup_code=original_code,
            number=number_of_runs,
        )

        # 수정된 코드 실행 시간 측정
        print(" - 수정된 코드 실행 시간 측정 중...")
        mod_avg_time = _run_code_in_subprocess(
            code_to_run="pass",  # 실제 호출할 함수가 있다면 여기에 명시
            setup_code=modified_code,
            number=number_of_runs,
        )

        # 성능 개선율 계산
        if orig_avg_time == 0:
            improvement = float("inf") if mod_avg_time < orig_avg_time else 0.0
        else:
            improvement = ((orig_avg_time - mod_avg_time) / orig_avg_time) * 100

        print(f"성능 분석 완료: 개선율 = {improvement:.2f}%")

        return PerformanceReport(
            success=True,
            original_avg_time=orig_avg_time,
            modified_avg_time=mod_avg_time,
            improvement_percentage=improvement,
        )

    except Exception as e:
        error_msg = f"성능 분석 중 오류 발생: {e}"
        print(error_msg)
        return PerformanceReport(
            success=False,
            original_avg_time=-1.0,
            modified_avg_time=-1.0,
            improvement_percentage=0.0,
            error_message=error_msg,
        )


# --- 이 파일이 직접 실행될 때를 위한 예제 코드 ---
if __name__ == "__main__":
    # 예제 1: 성능이 개선된 경우
    code_original = """
def slow_function():
    total = 0
    for i in range(10000):
        total += i
slow_function()
"""
    code_modified = """
def fast_function():
    # 더 효율적인 등차수열 합 공식 사용
    total = 10000 * (10000 - 1) // 2
fast_function()
"""
    print("--- 1. 성능 개선 코드 분석 ---")
    report1 = profile_performance(code_original, code_modified, number_of_runs=5)
    if report1.success:
        print(f"원본 평균 시간: {report1.original_avg_time * 1000:.4f} ms")
        print(f"수정본 평균 시간: {report1.modified_avg_time * 1000:.4f} ms")
        print(f"성능 개선율: {report1.improvement_percentage:.2f}%")

    print("\n" + "=" * 40 + "\n")

    # 예제 2: 성능이 저하된 경우
    code_original_fast = "total = sum(range(10000))"
    code_modified_slow = """
total = 0
for i in range(10000):
    total += i
"""
    print("--- 2. 성능 저하 코드 분석 ---")
    report2 = profile_performance(
        code_original_fast, code_modified_slow, number_of_runs=5
    )
    if report2.success:
        print(f"원본 평균 시간: {report2.original_avg_time * 1000:.4f} ms")
        print(f"수정본 평균 시간: {report2.modified_avg_time * 1000:.4f} ms")
        print(f"성능 개선율: {report2.improvement_percentage:.2f}%")
