import subprocess
import json
import tempfile
import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ReadabilityReport:
    success: bool
    average_complexity: float
    complexities: List[dict]
    error_message: Optional[str] = None

def analyze_readability(code: str) -> ReadabilityReport:
    """
    Radon을 사용하여 코드의 순환 복잡도(Cyclomatic Complexity)를 측정합니다.
    (Subprocess 격리 방식으로 안정성 강화)
    """
    if not code.strip():
        return ReadabilityReport(False, 0.0, [], "Empty code")

    # 임시 파일 생성 (Radon CLI는 파일을 입력으로 받음)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        # radon cc <file> --json 명령 실행
        result = subprocess.run(
            ["radon", "cc", tmp_path, "--json"],
            capture_output=True,
            text=True,
            timeout=10 # 10초 타임아웃
        )

        if result.returncode != 0:
            return ReadabilityReport(False, 0.0, [], f"Radon failed: {result.stderr}")

        # JSON 파싱
        # Radon output format: {"filename": [{"name": "func", "complexity": 1, ...}]}
        data = json.loads(result.stdout)
        
        # 파일명 키로 데이터 접근 (임시 파일 경로)
        file_data = data.get(tmp_path, [])
        
        if not file_data:
            # 함수가 없거나 분석할 내용이 없는 경우 (복잡도 1로 간주)
            return ReadabilityReport(True, 1.0, [], None)

        total_complexity = sum(item['complexity'] for item in file_data)
        avg_complexity = total_complexity / len(file_data)

        return ReadabilityReport(True, avg_complexity, file_data, None)

    except json.JSONDecodeError:
        return ReadabilityReport(False, 0.0, [], "Failed to parse Radon JSON output")
    except Exception as e:
        return ReadabilityReport(False, 0.0, [], str(e))
    finally:
        # 임시 파일 삭제
        if os.path.exists(tmp_path):
            os.remove(tmp_path)