import subprocess
import tempfile
import json
import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SecurityReport:
    success: bool
    highest_severity: Optional[str] # "LOW", "MEDIUM", "HIGH", None
    issues: List[dict]
    error_message: Optional[str] = None

def analyze_security(code: str) -> SecurityReport:
    """
    Bandit을 사용하여 보안 취약점을 분석합니다.
    """
    if not code.strip():
        return SecurityReport(False, None, [], "Empty code")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        # bandit -r <file> -f json
        # Bandit은 이슈가 발견되면 exit code 1을 반환하므로 check=False로 설정
        result = subprocess.run(
            ["bandit", "-r", tmp_path, "-f", "json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # JSON 파싱
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            # Bandit이 JSON을 출력하지 못한 경우 (문법 에러 등)
            return SecurityReport(False, None, [], f"Bandit failed: {result.stderr}")

        results = data.get("results", [])
        
        if not results:
            return SecurityReport(True, None, [], None)

        # 가장 높은 심각도 찾기
        severity_map = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        max_severity_val = 0
        highest_severity = None

        for issue in results:
            sev = issue.get("issue_severity", "LOW").upper()
            val = severity_map.get(sev, 1)
            if val > max_severity_val:
                max_severity_val = val
                highest_severity = sev

        return SecurityReport(True, highest_severity, results, None)

    except Exception as e:
        return SecurityReport(False, None, [], str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)