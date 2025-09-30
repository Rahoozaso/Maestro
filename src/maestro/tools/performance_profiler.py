import time
from dataclasses import dataclass
from typing import Optional

@dataclass
class ProfileResult:
    """성능 측정 결과를 담는 데이터 클래스"""
    success: bool
    time_before_ms: float
    time_after_ms: float
    improvement_percentage: float
    error_message: Optional[str] = None

def _run_and_measure(code_string: str, test_call: str, iterations: int) -> float:
    """
    주어진 코드 문자열을 실행하고 평균 실행 시간을 측정하는 헬퍼 함수.
    성공 시 평균 실행 시간(ms)을, 실패 시 -1.0을 반환합니다.
    """
    # 격리된 실행 환경(네임스페이스) 생성
    namespace = {}
    try:
        # 코드 문자열을 실행하여 함수 등을 메모리에 로드
        exec(code_string, namespace)
        
        # 실제 성능 측정 전 워밍업 실행 (선택 사항)
        exec(test_call, namespace)

        # 여러 번 실행하여 평균 시간 측정
        start_time = time.perf_counter()
        for _ in range(iterations):
            exec(test_call, namespace)
        end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_time_ms = (total_time / iterations) * 1000
        return avg_time_ms

    except Exception as e:
        print(f"코드 실행 중 오류 발생: {e}")
        return -1.0

def profile_performance_improvement(
    code_before: str, 
    code_after: str, 
    test_call: str, 
    iterations: int = 10
) -> ProfileResult:
    """
    리팩토링 전후 코드의 성능을 비교하고 개선율을 계산합니다.

    Args:
        code_before (str): 리팩토링 전 원본 코드 ('v_gen').
        code_after (str): 리팩토링 후 수정된 코드 ('v_final').
        test_call (str): 성능을 측정할 실제 함수 호출 코드 (e.g., "my_function(10)").
        iterations (int): 정확한 측정을 위한 반복 횟수.

    Returns:
        ProfileResult: 성능 측정 결과를 담은 객체.
    """
    print(f"성능 프로파일링 시작 (반복 횟수: {iterations})...")

    # 리팩토링 전 코드 성능 측정
    time_before = _run_and_measure(code_before, test_call, iterations)
    if time_before < 0:
        return ProfileResult(
            success=False, 
            time_before_ms=0, 
            time_after_ms=0, 
            improvement_percentage=0, 
            error_message="리팩토링 전 코드 실행에 실패했습니다."
        )

    # 리팩토링 후 코드 성능 측정
    time_after = _run_and_measure(code_after, test_call, iterations)
    if time_after < 0:
        return ProfileResult(
            success=False, 
            time_before_ms=time_before, 
            time_after_ms=0, 
            improvement_percentage=0, 
            error_message="리팩토링 후 코드 실행에 실패했습니다."
        )

    # 성능 개선율 계산
    if time_before == 0:
        improvement_percentage = 0.0
    else:
        improvement_percentage = ((time_before - time_after) / time_before) * 100

    print(f"프로파일링 완료: 이전={time_before:.4f}ms, 이후={time_after:.4f}ms, 개선율={improvement_percentage:.2f}%")
    
    return ProfileResult(
        success=True,
        time_before_ms=time_before,
        time_after_ms=time_after,
        improvement_percentage=improvement_percentage
    )

# --- 이 파일이 직접 실행될 때를 위한 예제 코드 ---
if __name__ == '__main__':
    # 예제: 비효율적인 리스트 검색 (리팩토링 전)
    code_before_example = """
def find_common_elements(list1, list2):
    common = []
    for item1 in list1:
        if item1 in list2:
            common.append(item1)
    return common
"""

    # 예제: 효율적인 세트 검색 (리팩토링 후)
    code_after_example = """
def find_common_elements(list1, list2):
    set2 = set(list2)
    common = [item1 for item1 in list1 if item1 in set2]
    return common
"""

    # 성능을 측정할 함수 호출 정의
    # 실제로는 HumanEval, SWE-Bench의 테스트 케이스를 기반으로 생성됩니다.
    large_list1 = list(range(1000))
    large_list2 = list(range(500, 1500))
    test_call_str = f"find_common_elements({large_list1}, {large_list2})"

    # 성능 프로파일러 실행
    result = profile_performance_improvement(
        code_before=code_before_example,
        code_after=code_after_example,
        test_call=test_call_str,
        iterations=50
    )

    # 결과 출력
    if result.success:
        print("\n--- 최종 결과 ---")
        print(f"성공 여부: {result.success}")
        print(f"리팩토링 전 평균 시간: {result.time_before_ms:.4f} ms")
        print(f"리팩토링 후 평균 시간: {result.time_after_ms:.4f} ms")
        print(f"성능 개선율: {result.improvement_percentage:.2f} %")
    else:
        print(f"\n성능 측정 실패: {result.error_message}")
