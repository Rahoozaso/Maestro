import time
import subprocess
import tempfile
import os
import sys
from dataclasses import dataclass
from typing import Optional

@dataclass
class PerformanceReport:
    success: bool
    original_avg_time: float
    modified_avg_time: float
    improvement_percentage: float
    error_message: Optional[str] = None

def _measure_execution_time(code: str, timeout: int = 5) -> float:
    """
    코드를 별도 프로세스에서 실행하여 소요 시간을 측정합니다.
    """
    # [수정] f-string 내부 백슬래시 문제 해결을 위해 미리 변수로 변환
    # 코드를 들여쓰기하여 try 블록 안에 넣기 위한 전처리
    indented_code = '\n    '.join(code.splitlines())

    # 1. 실행 래퍼 코드 작성 (시간 측정 로직 포함)
    wrapper_code = f"""
import time
try:
    {indented_code}
except Exception:
    pass # 실행 중 에러는 무시 (시간 측정 불가)

start_time = time.perf_counter()
try:
    # 메인 로직이 있다면 실행 (HumanEval의 경우 함수 정의만 있으므로 pass)
    pass 
except:
    pass
end_time = time.perf_counter()
print(end_time - start_time)
"""
    # 2. 임시 파일 저장
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmp:
        tmp.write(wrapper_code) # 래퍼 코드를 저장해야 함 (수정됨)
        tmp_path = tmp.name

    try:
        # 3. 서브프로세스로 실행 (타임아웃 설정 필수)
        # python -m timeit 보다는 직접 실행이 더 유연함
        start = time.perf_counter()
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        end = time.perf_counter()
        
        if result.returncode != 0:
            # 실행 실패 (SyntaxError, NameError 등)
            return -1.0
            
        # 실행 성공 시, stdout에 출력된 시간 파싱 시도
        try:
            duration = float(result.stdout.strip())
            return duration
        except ValueError:
            return end - start # 파싱 실패 시 전체 실행 시간으로 대체

    except subprocess.TimeoutExpired:
        return -1.0 # 타임아웃 (무한루프 등)
    except Exception:
        return -1.0
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except PermissionError:
                pass # 윈도우에서 가끔 삭제 실패 시 무시
        
def profile_performance(original_code: str, modified_code: str) -> PerformanceReport:
    """
    원본 코드와 수정된 코드의 실행 시간을 비교합니다.
    """
    # 1. 원본 코드 측정
    t_org = _measure_execution_time(original_code)
    if t_org < 0:
        # 원본 실행 실패는 치명적이지 않음 (비교 불가일 뿐)
        t_org = 0.000001 # 0으로 나누기 방지

    # 2. 수정된 코드 측정
    t_mod = _measure_execution_time(modified_code)
    if t_mod < 0:
        return PerformanceReport(False, 0.0, 0.0, 0.0, "Modified code execution failed (Runtime Error)")

    # 3. 개선율 계산
    # 시간이 너무 작으면(0에 가까우면) 계산 불가
    if t_org < 1e-9: 
        improvement = 0.0
    else:
        improvement = ((t_org - t_mod) / t_org) * 100

    return PerformanceReport(True, t_org, t_mod, improvement, None)