import json
import os
import yaml
from typing import Any, Dict


def read_text_file(filepath: str) -> str:
    """
    주어진 경로의 텍스트 파일을 읽어 문자열로 반환합니다.
    주로 프롬프트 템플릿이나 소스 코드를 읽는 데 사용됩니다.

    Args:
        filepath (str): 읽을 파일의 경로.

    Returns:
        str: 파일의 전체 내용.

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 경우.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없습니다: {filepath}")
        raise


def write_text_file(filepath: str, content: str) -> None:
    """
    주어진 내용(content)을 지정된 경로의 텍스트 파일에 씁니다.
    파일을 쓰기 전에 상위 폴더가 존재하지 않으면 자동으로 생성합니다.

    Args:
        filepath (str): 쓸 파일의 경로.
        content (str): 파일에 쓸 내용.
    """
    try:
        # 파일이 저장될 폴더 경로를 가져옵니다.
        dir_path = os.path.dirname(filepath)
        # 폴더가 존재하지 않으면 생성합니다.
        os.makedirs(dir_path, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"파일 저장 완료: {filepath}")
    except IOError as e:
        print(f"파일 쓰기 중 오류 발생: {e}")


def read_yaml_file(filepath: str) -> Dict:
    """
    YAML 설정 파일을 읽어 파이썬 딕셔너리로 반환합니다.

    Args:
        filepath (str): 읽을 YAML 파일의 경로.

    Returns:
        Dict: YAML 파일의 내용.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as stream:
            return yaml.safe_load(stream)
    except FileNotFoundError:
        print(f"오류: YAML 파일을 찾을 수 없습니다: {filepath}")
        raise
    except yaml.YAMLError as e:
        print(f"YAML 파싱 중 오류 발생: {e}")
        raise


def write_json_file(filepath: str, data: Any, indent: int = 4) -> None:
    """
    파이썬 객체(딕셔너리, 리스트 등)를 JSON 파일로 저장합니다.

    Args:
        filepath (str): 저장할 JSON 파일의 경로.
        data (Any): 저장할 파이썬 객체.
        indent (int): 가독성을 위한 들여쓰기 칸 수.
    """
    try:
        dir_path = os.path.dirname(filepath)
        os.makedirs(dir_path, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            # ensure_ascii=False를 통해 한글이 깨지지 않도록 합니다.
            json.dump(data, f, ensure_ascii=False, indent=indent)
        print(f"JSON 파일 저장 완료: {filepath}")
    except (IOError, TypeError) as e:
        print(f"JSON 파일 저장 중 오류 발생: {e}")
