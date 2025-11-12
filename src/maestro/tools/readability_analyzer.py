from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from radon.complexity import cc_visit


@dataclass
class ReadabilityReport:
    """가독성 분석 결과를 담는 데이터 클래스"""

    success: bool
    average_complexity: float
    # (함수/메서드 이름, 복잡도 점수) 형태의 튜플 리스트
    complexities: List[Tuple[str, int]] = field(default_factory=list)
    error_message: Optional[str] = None


def analyze_readability(code_string: str) -> ReadabilityReport:
    """
    주어진 코드 문자열의 순환 복잡도를 분석합니다.

    Args:
        code_string (str): 분석할 Python 코드.

    Returns:
        ReadabilityReport: 가독성 분석 결과를 담은 객체.
    """
    print("가독성 분석 시작 (순환 복잡도 측정)...")
    try:
        # radon을 사용하여 코드 블록들의 복잡도 분석
        blocks = cc_visit(code_string)

        if not blocks:
            # 분석할 함수나 클래스가 없는 경우
            return ReadabilityReport(
                success=True, average_complexity=1.0, complexities=[]
            )

        total_complexity = 0
        detailed_complexities = []
        for block in blocks:
            # 블록 타입(Function, Method 등)과 이름, 복잡도 점수를 저장
            block_name = f"{block.name} ({block.type})"
            detailed_complexities.append((block_name, block.complexity))
            total_complexity += block.complexity

        average_complexity = total_complexity / len(blocks)

        print(f"가독성 분석 완료: 평균 복잡도={average_complexity:.2f}")

        return ReadabilityReport(
            success=True,
            average_complexity=average_complexity,
            complexities=detailed_complexities,
        )

    except Exception as e:
        # 코드가 문법적으로 올바르지 않아 파싱에 실패하는 경우 등
        error_msg = f"가독성 분석 중 오류 발생: {e}"
        print(error_msg)
        return ReadabilityReport(
            success=False, average_complexity=-1.0, error_message=error_msg
        )


# --- 이 파일이 직접 실행될 때를 위한 예제 코드 ---
if __name__ == "__main__":
    # 예제 1: 가독성이 좋은 코드 (낮은 복잡도)
    code_good_example = """
def is_eligible(age):
    if age < 18:
        return False
    return True

def get_greeting(name):
    return f"Hello, {name}!"
"""

    # 예제 2: 가독성이 나쁜 코드 (높은 복잡도)
    code_bad_example = """
def process_data(user_type, age, country, has_coupon):
    if user_type == "premium":
        if age > 18:
            if country == "KR":
                if has_coupon:
                    return "Offer A"
                else:
                    return "Offer B"
            else:
                return "Offer C"
        else:
            return "Offer D"
    else:
        if age > 20 and (country == "US" or country == "KR"):
            return "Offer E"
    return "No Offer"
"""

    print("--- 1. 가독성 좋은 코드 분석 ---")
    report_good = analyze_readability(code_good_example)
    if report_good.success:
        print(f"평균 복잡도: {report_good.average_complexity:.2f}")
        for name, score in report_good.complexities:
            print(f" - {name}: {score}")

    print("\n" + "=" * 40 + "\n")

    print("--- 2. 가독성 나쁜 코드 분석 ---")
    report_bad = analyze_readability(code_bad_example)
    if report_bad.success:
        print(f"평균 복잡도: {report_bad.average_complexity:.2f}")
        for name, score in report_bad.complexities:
            print(f" - {name}: {score}")
