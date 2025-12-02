"""
Main module implementing a simple, SRP-focused data pipeline.

Responsibilities
- Parse CLI arguments (input source and output destination).
- Load input data from a file path or stdin (JSON expected).
- Validate the loaded data with clear guard clauses for early failure.
- Transform the data into a summarized structure.
- Persist the result to a file path or stdout.

Inputs/Outputs
- Input: JSON via a file path or stdin (use '-' or omit --input to read stdin).
- Output: JSON written to a file path or stdout (use '-' or omit --output for stdout).

Side Effects
- Filesystem I/O if file paths are provided.
- Reads from stdin and writes to stdout/stderr when specified or by default.
"""

from typing import Any, List, Optional, Tuple
import argparse
import json
import sys
from pathlib import Path


def load_input(source: Optional[str]) -> Any:
    """Load JSON input from a file path or stdin using guard clauses.

    Args:
        source: Path to input file or '-'/None for stdin.

    Returns:
        Parsed JSON object.

    Raises:
        ValueError: If input cannot be read or parsed as JSON.
    """
    # Guard clause: read from stdin when source is not provided or is '-'
    if not source or source == "-":
        raw = sys.stdin.read()
        if not raw.strip():
            raise ValueError("No input provided on stdin.")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON from stdin: {exc}") from exc

    # Guard clause: ensure path exists and is a file
    path = Path(source)
    if not path.exists() or not path.is_file():
        raise ValueError(f"Input path does not exist or is not a file: {source}")

    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse JSON from file '{source}': {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Failed to read input file '{source}': {exc}") from exc


essages = Tuple[bool, List[str]]


def validate(data: Any) -> Tuple[bool, List[str]]:
    """Validate the loaded data with early exits.

    Rules:
    - Data must be a JSON object (dict) or array (list).

    Returns:
        A tuple of (is_valid, messages). If not valid, messages contain reasons.
    """
    # Guard: None or empty string
    if data is None:
        return False, ["Input data is None."]

    # Guard: Only dict or list allowed
    if not isinstance(data, (dict, list)):
        return False, [
            f"Invalid data type: {type(data).__name__}. Expected JSON object or array."
        ]

    # Additional simple checks (examples)
    if isinstance(data, dict) and len(data) == 0:
        return False, ["Input object must not be empty."]

    if isinstance(data, list) and len(data) == 0:
        return False, ["Input array must not be empty."]

    return True, ["Input data is valid."]


def transform(data: Any) -> Any:
    """Transform the input data into a summarized structure.

    - For a dict: returns the original keys and a processed flag.
    - For a list: returns a summary with length and primitive type counts.
    """
    # Guard: handle dict
    if isinstance(data, dict):
        return {
            "type": "object",
            "processed": True,
            "keys": sorted(list(data.keys())),
            "size": len(data),
        }

    # Guard: handle list
    if isinstance(data, list):
        primitive_counts = {"str": 0, "int": 0, "float": 0, "bool": 0, "null": 0, "other": 0}
        for item in data:
            if item is None:
                primitive_counts["null"] += 1
            elif isinstance(item, bool):
                primitive_counts["bool"] += 1
            elif isinstance(item, int) and not isinstance(item, bool):
                primitive_counts["int"] += 1
            elif isinstance(item, float):
                primitive_counts["float"] += 1
            elif isinstance(item, str):
                primitive_counts["str"] += 1
            else:
                primitive_counts["other"] += 1
        return {
            "type": "array",
            "processed": True,
            "length": len(data),
            "primitive_counts": primitive_counts,
        }

    # Guard: should not reach here if validate() is used properly
    return {"type": "unknown", "processed": False}


def persist(result: Any, destination: Optional[str]) -> None:
    """Persist the result as JSON to a file or stdout."""
    payload = json.dumps(result, ensure_ascii=False, indent=2)

    # Guard: write to stdout
    if not destination or destination == "-":
        sys.stdout.write(payload + "\n")
        return

    # Guard: write to file
    path = Path(destination)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.write("\n")
    except OSError as exc:
        raise ValueError(f"Failed to write output file '{destination}': {exc}") from exc


def process(source: Optional[str], destination: Optional[str]) -> int:
    """Orchestrate the pipeline with clear guard clauses and early returns.

    Returns an exit code suitable for sys.exit.
    """
    # Load
    try:
        data = load_input(source)
    except ValueError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 2

    # Validate
    is_valid, messages = validate(data)
    if not is_valid:
        for msg in messages:
            sys.stderr.write(f"Validation error: {msg}\n")
        return 3

    # Transform
    try:
        result = transform(data)
    except Exception as exc:  # Guard: unexpected transform errors
        sys.stderr.write(f"Transform failed: {exc}\n")
        return 4

    # Persist
    try:
        persist(result, destination)
    except ValueError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 5

    return 0


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SRP-focused JSON pipeline")
    parser.add_argument(
        "--input",
        "-i",
        dest="input",
        default=None,
        help="Input file path or '-' for stdin (default: stdin)",
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="output",
        default=None,
        help="Output file path or '-' for stdout (default: stdout)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    exit_code = process(args.input, args.output)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()