import json
import subprocess
import tempfile
import os
from dataclasses import dataclass, field
from typing import List, Optional, Literal

# Bandit의 심각도 레벨 정의
SeverityLevel = Literal["HIGH", "MEDIUM", "LOW", "UNDEFINED"]

@dataclass
class SecurityIssue:
    """Bandit이 발견한 개별 보안 이슈를 담는 데이터 클래스"""
    severity: SeverityLevel
    confidence: str
    cwe: str
    code: str
    line_number: int
    issue_text: str

@dataclass
class SecurityReport:
    """보안 분석 전체 결과를 담는 데이터 클래스"""
    success: bool
    highest_severity: Optional[SeverityLevel] = None
    issues: List[SecurityIssue] = field(default_factory=list)
    error_message: Optional[str] = None

def analyze_security(code_string: str) -> SecurityReport:
    """
    주어진 코드 문자열의 보안 취약점을 Bandit으로 분석합니다.

    Args:
        code_string (str): 분석할 Python 코드.

    Returns:
        SecurityReport: 보안 분석 결과를 담은 객체.
    """
    print("보안 분석 시작 (Bandit 스캔)...")
    # 임시 파일을 생성하여 코드 문자열을 저장합니다.
    # delete=False로 설정하여 파일 경로를 직접 사용하고, 수동으로 삭제합니다.
    try:
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.py', encoding='utf-8') as temp_file:
            temp_file.write(code_string)
            temp_filepath = temp_file.name
        
        # Bandit을 JSON 포맷으로 실행하는 명령어
        command = [
            "bandit",
            "-r", temp_filepath,
            "-f", "json"
        ]

        # Bandit 실행
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')

        if result.returncode != 0 and not result.stdout:
            # Bandit 실행 자체가 실패한 경우
            error_msg = f"Bandit 실행 실패: {result.stderr}"
            print(error_msg)
            return SecurityReport(success=False, error_message=error_msg)

        # Bandit 결과(JSON) 파싱
        try:
            bandit_results = json.loads(result.stdout)
        except json.JSONDecodeError:
            error_msg = "Bandit 출력 JSON 파싱 실패."
            print(error_msg)
            return SecurityReport(success=False, error_message=error_msg)
            
        issues = []
        severity_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNDEFINED": 0}
        highest_severity_level = 0
        highest_severity_str: Optional[SeverityLevel] = None

        for issue_data in bandit_results.get("results", []):
            severity = issue_data.get("issue_severity", "UNDEFINED")
            
            issue = SecurityIssue(
                severity=severity,
                confidence=issue_data.get("issue_confidence", "UNDEFINED"),
                cwe=issue_data.get("test_id", "N/A"),
                code=issue_data.get("code", ""),
                line_number=issue_data.get("line_number", -1),
                issue_text=issue_data.get("issue_text", "")
            )
            issues.append(issue)

            if severity_map.get(severity, 0) > highest_severity_level:
                highest_severity_level = severity_map[severity]
                highest_severity_str = severity
        
        print(f"보안 분석 완료: {len(issues)}개의 이슈 발견, 최고 심각도: {highest_severity_str or 'None'}")
        
        return SecurityReport(
            success=True,
            highest_severity=highest_severity_str,
            issues=issues
        )

    except Exception as e:
        error_msg = f"보안 분석 중 예외 발생: {e}"
        print(error_msg)
        return SecurityReport(success=False, error_message=error_msg)
    
    finally:
        # 임시 파일 정리
        if 'temp_filepath' in locals() and os.path.exists(temp_filepath):
            os.remove(temp_filepath)

# --- 이 파일이 직접 실행될 때를 위한 예제 코드 ---
if __name__ == '__main__':
    # 예제 1: 보안 취약점이 있는 코드 (하드코딩된 비밀번호)
    code_vulnerable_example = """
import os

API_KEY = "sk-this_is_a_fake_key_for_testing_purposes" # HIGH severity

def get_data():
    # 'requests' 라이브러리가 설치되어 있다고 가정
    # import requests
    # response = requests.get("https://api.example.com", headers={"Authorization": f"Bearer {API_KEY}"})
    # return response.json()
    pass

def run_command(command):
    os.system(f"echo {command}") # MEDIUM severity
"""

    # 예제 2: 깨끗한 코드
    code_clean_example = """
def add(a, b):
    return a + b
"""
    print("--- 1. 취약점이 있는 코드 분석 ---")
    report_vuln = analyze_security(code_vulnerable_example)
    if report_vuln.success:
        print(f"최고 심각도: {report_vuln.highest_severity}")
        for issue in report_vuln.issues:
            print(f" - [L{issue.line_number}] {issue.severity}: {issue.issue_text}")

    print("\n" + "="*40 + "\n")

    print("--- 2. 깨끗한 코드 분석 ---")
    report_clean = analyze_security(code_clean_example)
    if report_clean.success:
        print(f"최고 심각도: {report_clean.highest_severity or 'None'}")
        print(f"발견된 이슈: {len(report_clean.issues)}개")
