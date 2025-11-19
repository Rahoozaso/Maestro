"""
Main module providing a small, readable CLI scaffold.

Purpose:
- Demonstrate clear structure using early returns (guard clauses) and small, focused functions.
- Serve as an example entry point that loads a JSON config, validates it, and executes a simple task.

Responsibilities:
- Parse command-line arguments.
- Load and validate a JSON configuration file.
- Execute a trivial pipeline on input data (e.g., scale and offset a list of numbers).

Inputs/Outputs:
- Input: Path to a JSON config file containing fields like {"scale": float, "offset": float, "items": [numbers]}.
- Output: Prints results to stdout and exits with code 0 on success; non-zero on failure.

Usage example:
  python -m main --config ./config.json

Example config.json:
  {
    "scale": 2.0,
    "offset": 1.0,
    "items": [1, 2, 3]
  }

Expected output:
  3.0, 5.0, 7.0
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Config:
    scale: float
    offset: float
    items: List[float]


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Readable CLI scaffold with guard clauses")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to JSON configuration file."
    )
    return parser.parse_args(argv)


def load_json(path: str) -> Tuple[Optional[dict], Optional[str]]:
    """Load JSON from path.

    Returns a tuple of (data, error_message). On success, error_message is None.
    Uses early returns to keep flow shallow.
    """
    if not path:
        return None, "Config path is empty"

    if not os.path.exists(path):
        return None, f"Config file not found: {path}"

    if not os.path.isfile(path):
        return None, f"Config path is not a file: {path}"

    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh), None
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON: {exc}"
    except OSError as exc:
        return None, f"Failed to read file: {exc}"


def validate_config_dict(cfg: dict) -> Optional[str]:
    """Validate raw config dict. Return None if valid, else an error message.

    Guard-style checks return immediately upon detecting an issue.
    """
    if not isinstance(cfg, dict):
        return "Config must be a JSON object"

    # Required keys
    for key in ("scale", "offset", "items"):
        if key not in cfg:
            return f"Missing required key: {key}"

    # Type checks
    if not isinstance(cfg["scale"], (int, float)):
        return "'scale' must be a number"
    if not isinstance(cfg["offset"], (int, float)):
        return "'offset' must be a number"
    if not isinstance(cfg["items"], list):
        return "'items' must be a list"

    # Validate items
    for i, val in enumerate(cfg["items"]):
        if not isinstance(val, (int, float)):
            return f"items[{i}] must be a number"

    return None


def build_config(cfg: dict) -> Config:
    """Convert dict to Config dataclass."""
    return Config(scale=float(cfg["scale"]), offset=float(cfg["offset"]), items=[float(v) for v in cfg["items"]])


def transform_items(items: Iterable[float], scale: float, offset: float) -> List[float]:
    """Apply a simple linear transform to a sequence of numbers.

    Uses early exits for degenerate cases.
    """
    # Handle degenerate inputs early
    if items is None:
        return []

    result: List[float] = []
    for v in items:
        result.append(v * scale + offset)
    return result


def execute(cfg: Config) -> int:
    """Execute the main job. Returns exit code.

    Keeps branching shallow and delegates to small functions.
    """
    if not cfg.items:
        # No work to do is a successful no-op
        return 0

    transformed = transform_items(cfg.items, cfg.scale, cfg.offset)
    if not transformed:
        # Nothing produced but not an error condition in this trivial pipeline
        return 0

    print(", ".join(str(x) for x in transformed))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    data, err = load_json(args.config)
    if err is not None:
        print(f"Error: {err}", file=sys.stderr)
        return 2

    err = validate_config_dict(data)
    if err is not None:
        print(f"Error: {err}", file=sys.stderr)
        return 2

    cfg = build_config(data)
    return execute(cfg)


if __name__ == "__main__":
    raise SystemExit(main())