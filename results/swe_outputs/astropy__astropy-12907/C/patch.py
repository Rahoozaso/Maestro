from __future__ import annotations

import ast
import json
import subprocess
from typing import Any, Iterable, List, NoReturn, Optional, Union

import yaml

"""
Main module implementing secure and readable patterns as per execution plan.

This module provides:
- Secure SQL query execution helpers (parameterized queries).
- Safe subprocess execution without shell=True.
- Safe YAML loading and disabled unsafe pickle deserialization.
- Safe literal evaluation to replace eval.
- Refactored SRP-style data processing pipeline with clear helpers.
- Performance-safe string concatenation utility.
- Lazy imports for heavy/optional dependencies.

All functions include concise docstrings with responsibilities and usage guidance.
"""

# -----------------------------
# Constants (READ-005)
# -----------------------------
ADMIN_LEVEL_THRESHOLD: int = 5
HTTP_OK: int = 200
DEFAULT_BACKOFF: float = 0.05
STATUS_PROCESSED: str = "processed"


# -----------------------------
# Security helpers (SEC-001, SEC-002, SEC-005, SEC-009)
# -----------------------------

def secure_fetch_user(cursor: Any, username: str, status: str) -> List[tuple]:
    """Fetch user rows securely using parameterized SQL queries.

    Args:
        cursor: PEP 249 DB-API compatible cursor.
        username: Username to query.
        status: Status to filter by.

    Returns:
        A list of rows returned by the query.
    """
    # SEC-001: parameterized query prevents SQL injection
    cursor.execute("SELECT * FROM users WHERE username = ? AND status = ?", (username, status))
    try:
        return list(cursor.fetchall())
    except Exception:
        # Some DB-API cursors do not support fetchall after non-SELECT.
        return []


def run_command(cmd: str, *args: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    """Run a system command safely without shell=True.

    Args:
        cmd: Absolute or resolvable path to the executable.
        *args: Arguments to pass to the command.
        timeout: Timeout in seconds for the command execution.

    Returns:
        subprocess.CompletedProcess with text stdout/stderr.

    Raises:
        subprocess.CalledProcessError: If the command exits with non-zero status.
        subprocess.TimeoutExpired: If the command times out.
    """
    assert isinstance(cmd, str)
    safe_args = [cmd] + [str(a) for a in args]
    return subprocess.run(safe_args, check=True, capture_output=True, text=True, timeout=timeout)


def load_yaml_safe(yaml_str: str) -> Any:
    """Safely load YAML using yaml.safe_load.

    Args:
        yaml_str: YAML content as a string.

    Returns:
        Parsed Python object.
    """
    # SEC-005: use safe loader
    return yaml.safe_load(yaml_str)


def unsafe_pickle_loads(_: bytes) -> NoReturn:
    """Disabled pickle deserialization.

    Raises:
        RuntimeError: Always, to indicate insecure operation is disabled.
    """
    # SEC-005: disable unsafe deserialization from untrusted sources
    raise RuntimeError("pickle deserialization is disabled for security reasons")


def safe_literal_eval(user_supplied_literal: str) -> Any:
    """Safely evaluate a user-supplied Python literal.

    Args:
        user_supplied_literal: A string containing a Python literal (e.g., list, dict, str, number).

    Returns:
        The parsed Python value.

    Raises:
        ValueError: If the string cannot be parsed as a literal.
    """
    # SEC-009: replace eval with ast.literal_eval
    try:
        return ast.literal_eval(user_supplied_literal)
    except Exception as exc:
        raise ValueError(f"Invalid literal: {exc}") from exc


# -----------------------------
# Performance helper (PERF-STRING-JOIN-002)
# -----------------------------

def concat_strings(pieces: Iterable[str]) -> str:
    """Concatenate strings efficiently using join on a list of fragments.

    Args:
        pieces: Iterable of string fragments.

    Returns:
        Concatenated string.
    """
    out: List[str] = []
    append = out.append
    for p in pieces:
        append(p)
    return "".join(out)


# -----------------------------
# Lazy import helpers (PERF-LAZY-IMPORT-004)
# -----------------------------

def read_csv_fast(path: str):
    """Read a CSV file with lazy import of pandas.

    Args:
        path: Path to CSV file.

    Returns:
        pandas.DataFrame
    """
    from pandas import read_csv  # lazy and specific

    return read_csv(path)


def optional_heavy_op(x: Optional[Iterable[Any]]):
    """Perform an optional heavy operation only when needed.

    Args:
        x: Optional iterable of values.

    Returns:
        Numpy array if x is provided; otherwise None.
    """
    if not x:
        return None
    import numpy as np  # imported only if needed

    return np.asarray(list(x))


# -----------------------------
# SRP pipeline example (READ-008, READ-007, READ-004, READ-003)
# -----------------------------

def load_input(data: Union[str, Iterable[dict]]) -> List[dict]:
    """Load input records from a YAML string or an iterable of dicts.

    Args:
        data: YAML string or iterable of mapping records.

    Returns:
        List of records (dicts).
    """
    if isinstance(data, str):
        parsed = load_yaml_safe(data)  # could be list[dict] or dict
        if isinstance(parsed, dict):
            return [parsed]
        if isinstance(parsed, list):
            return [r for r in parsed if isinstance(r, dict)]
        return []
    # If it's already an iterable of dicts
    return [r for r in data if isinstance(r, dict)]


def validate_input(records: List[dict]) -> List[dict]:
    """Validate records, using early returns to avoid deep nesting.

    Each record must contain 'id' and 'value'.

    Args:
        records: Input records.

    Returns:
        Validated records only.
    """
    valid: List[dict] = []
    for rec in records:
        if not isinstance(rec, dict):
            continue  # guard clause
        if 'id' not in rec or 'value' not in rec:
            continue  # guard clause
        valid.append(rec)
    return valid


def transform(records: List[dict]) -> List[dict]:
    """Transform records into processed output using explicit loops.

    - Avoid nested comprehensions for readability.
    - Demonstrates use of constants and helper functions.

    Args:
        records: Valid records to process.

    Returns:
        Transformed records with status and summary fields.
    """
    results: List[dict] = []
    for rec in records:
        # Example: compute a simple summary string safely
        summary_parts = ["ID=", str(rec.get('id')), ";VALUE=", str(rec.get('value'))]
        summary = concat_strings(summary_parts)
        out = {
            'id': rec['id'],
            'value': rec['value'],
            'status': STATUS_PROCESSED,
            'summary': summary,
            'http': HTTP_OK,
        }
        results.append(out)
    return results


def save_output(records: List[dict], pretty: bool = True) -> str:
    """Serialize processed records to JSON.

    Args:
        records: Records to serialize.
        pretty: Whether to pretty-print JSON.

    Returns:
        JSON string.
    """
    if pretty:
        return json.dumps(records, indent=2, sort_keys=True)
    return json.dumps(records)


def main(data: Union[str, Iterable[dict]]) -> str:
    """Orchestrate the pipeline with SRP and minimal control logic.

    Args:
        data: YAML string or iterable of dict records.

    Returns:
        JSON string of processed output.
    """
    records = load_input(data)
    valid = validate_input(records)
    transformed = transform(valid)
    output = save_output(transformed, pretty=True)
    return output


if __name__ == "__main__":
    # Minimal self-test example (no external dependencies)
    sample_yaml = """
    - id: 1
      value: 10
    - id: 2
      value: 20
    - id_only: 3
    """
    print(main(sample_yaml))