from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Mapping, Optional, Sequence, TypedDict

"""
A small module demonstrating a refactored, readable, and efficient data-processing
pipeline. It showcases guard clauses, SRP via focused helpers, typed interfaces
(no typing.Any), readable loops in place of complex comprehensions, and efficient
string building using join buffers.
"""

# Extracted constants to replace magic numbers/strings
ADMIN_LEVEL_THRESHOLD: int = 5
DEFAULT_TIMEOUT_MS: int = 1000
STATUS_PROCESSED: str = "processed"


class Record(TypedDict):
    """Structured representation of a record parsed from a CSV line.

    Keys
    ----
    id: Unique integer identifier for the record.
    name: Human-readable name.
    status: Current status string (e.g., 'processed', 'pending').
    level: A privilege or classification level.
    """

    id: int
    name: str
    status: str
    level: int


class User(TypedDict):
    """Structured representation of a user interacting with the system.

    Keys
    ----
    id: Unique integer identifier for the user.
    name: Human-readable username.
    level: The user's privilege level.
    active: Whether the user account is active.
    """

    id: int
    name: str
    level: int
    active: bool


def is_valid_user(user: Optional[User]) -> bool:
    """Determine if a provided user is valid and active.

    Args:
        user: Optional user structure.

    Returns:
        True if the user exists, is active, and meets minimal level requirements.
    """
    if user is None:
        return False
    if not user.get("active", False):
        return False
    # Guard for minimal level requirements
    return user.get("level", 0) >= 0


def read_file(path: str) -> str:
    """Read the entire contents of a text file.

    Args:
        path: Path to the file.

    Returns:
        The file content as a string.

    Raises:
        FileNotFoundError: If the path does not exist.
        IsADirectoryError: If the path points to a directory.
        OSError: For other I/O related errors.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if p.is_dir():
        raise IsADirectoryError(f"Expected file but found directory: {path}")

    # Early return keeps nesting shallow
    with p.open("r", encoding="utf-8") as fh:
        return fh.read()


def parse_records(raw: str) -> List[Record]:
    """Parse records from CSV text.

    Expected CSV header: id,name,status,level

    Args:
        raw: Raw CSV text.

    Returns:
        A list of parsed Record entries.
    """
    output_records: List[Record] = []

    # Use csv module for robust parsing
    reader = csv.DictReader(raw.splitlines())
    for row in reader:
        # Guard clauses to keep control flow simple
        if not row:
            continue
        try:
            rec: Record = {
                "id": int(row.get("id", "").strip()),
                "name": (row.get("name", "").strip()),
                "status": (row.get("status", "").strip()),
                "level": int(row.get("level", "").strip()),
            }
        except ValueError:
            # Skip rows that can't be parsed cleanly
            continue
        output_records.append(rec)

    return output_records


def validate_records(records: Sequence[Record]) -> List[Record]:
    """Filter out invalid records.

    A record is considered valid if:
    - id >= 0
    - name is not empty
    - status is not empty
    - level >= 0

    Args:
        records: Sequence of parsed records.

    Returns:
        A new list containing only valid records.
    """
    valid: List[Record] = []
    for rec in records:
        if rec["id"] < 0:
            continue
        if not rec["name"]:
            continue
        if not rec["status"]:
            continue
        if rec["level"] < 0:
            continue
        valid.append(rec)
    return valid


def transform_records(records: Sequence[Record], *, current_user: Optional[User] = None) -> List[str]:
    """Transform records into presentation-ready strings.

    Includes examples of:
    - Guard clauses for invalid user
    - Efficient string assembly using list buffering and join

    Args:
        records: Validated records to transform.
        current_user: Optional user context that can influence transformation.

    Returns:
        A list of presentation-ready strings.
    """
    # Guard: if user is provided but invalid, return early with no transformation
    if current_user is not None and not is_valid_user(current_user):
        return []

    output_lines: List[str] = []
    for rec in records:
        # Extract complex predicate into well-named boolean
        is_admin_view = current_user is not None and current_user.get("level", 0) >= ADMIN_LEVEL_THRESHOLD
        is_processed = rec["status"].lower() == STATUS_PROCESSED

        # Compose line components using list buffer to avoid O(n^2) concatenation
        parts: List[str] = [
            f"#{rec['id']}",
            rec["name"],
            f"status={rec['status']}",
            f"level={rec['level']}",
        ]
        if is_admin_view:
            parts.append("view=admin")
        if is_processed:
            parts.append("✓")

        output_lines.append(" | ".join(parts))

    return output_lines


def flatten_valid_records(groups: Iterable[Iterable[Record]]) -> List[Record]:
    """Flatten nested collections of records into a single validated list.

    This function intentionally uses a readable loop instead of a complex nested
    list comprehension.

    Args:
        groups: Iterable of record iterables.

    Returns:
        Flattened list of records.
    """
    flattened: List[Record] = []
    for group in groups:
        for rec in group:
            flattened.append(rec)
    return flattened


def process_file(path: str, *, user: Optional[User] = None) -> List[str]:
    """High-level coordinator to read, parse, validate, and transform records.

    Demonstrates Single Responsibility Principle (SRP) by delegating specific tasks
    to focused helper functions and keeping orchestration concise.

    Args:
        path: File path to a CSV with records.
        user: Optional User context.

    Returns:
        A list of transformed record strings ready for presentation.
    """
    # Guard clauses for invalid preconditions
    if not path:
        return []

    if user is not None and not is_valid_user(user):
        # Early return reduces nesting and clarifies control flow
        return []

    raw = read_file(path)
    parsed = parse_records(raw)
    validated = validate_records(parsed)
    output_lines = transform_records(validated, current_user=user)
    return output_lines


def generate_report(output_lines: Sequence[str]) -> str:
    """Generate a single report string from lines using efficient joining.

    Args:
        output_lines: Lines to include in the report.

    Returns:
        A single string containing the full report with newline separators.
    """
    # Efficient join replaces repeated string concatenation in a loop
    return "\n".join(output_lines)


__all__ = [
    "Record",
    "User",
    "ADMIN_LEVEL_THRESHOLD",
    "DEFAULT_TIMEOUT_MS",
    "STATUS_PROCESSED",
    "is_valid_user",
    "read_file",
    "parse_records",
    "validate_records",
    "transform_records",
    "flatten_valid_records",
    "process_file",
    "generate_report",
]