from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Mapping, MutableMapping, Sequence

import numpy as np
import pandas as pd

"""
main.py

A small, self-contained module demonstrating clean architecture principles:
- Cohesive helper functions (parse_input, validate_user, compute_metrics, format_response)
- Early returns and guard clauses to reduce nesting
- Readable loops instead of complex list comprehensions
- Precise typing and structured data via dataclasses
- Vectorized NumPy/Pandas operations instead of Python loops/apply
- Clear docstrings and organized imports

This module exposes a simple processing pipeline via process_request and
utility functions to demonstrate vectorized operations.
"""

# ------------------------------
# Named constants (avoid magic values)
# ------------------------------
ADMIN_LEVEL_THRESHOLD: int = 5
RETRY_LIMIT: int = 3
STATUS_PROCESSED: str = "processed"


# ------------------------------
# Structured data models
# ------------------------------
@dataclass(frozen=True)
class User:
    """Represents an application user.

    Attributes:
        id: Unique identifier for the user.
        name: Display name.
        level: Permission level; must be >= ADMIN_LEVEL_THRESHOLD to process.
        is_active: Whether the user is enabled.
    """

    id: int
    name: str
    level: int
    is_active: bool = True


@dataclass(frozen=True)
class Item:
    """Simple item used for metrics computation.

    Attributes:
        id: Unique identifier for the item.
        value: Numeric value associated with the item.
        tag: Optional tag for filtering/annotation.
    """

    id: int
    value: float
    tag: str = ""


logger = logging.getLogger(__name__)


# ------------------------------
# Helper functions
# ------------------------------

def parse_input(payload: Mapping[str, str]) -> dict[str, str]:
    """Validate and normalize the incoming payload.

    Args:
        payload: Mapping with required keys: "id", "name", and "level".

    Returns:
        A shallow-copied, normalized dictionary.

    Raises:
        KeyError: If required keys are missing.
        ValueError: If field types are invalid or empty.
    """
    required = ("id", "name", "level")
    for key in required:
        if key not in payload:
            raise KeyError(f"Missing required key: {key}")

    normalized: dict[str, str] = dict(payload)

    # Basic normalization/validation
    if not normalized["name"].strip():
        raise ValueError("Field 'name' must be non-empty")

    # Validate that id and level are numeric strings
    try:
        int(normalized["id"])  # type-check
        int(normalized["level"])  # type-check
    except (TypeError, ValueError) as exc:
        raise ValueError("Fields 'id' and 'level' must be integer-convertible") from exc

    return normalized


def _build_user(payload: Mapping[str, str]) -> User:
    """Construct a User from a validated payload.

    Args:
        payload: Mapping containing 'id', 'name', and 'level'. Assumed validated.

    Returns:
        A User instance.

    Raises:
        ValueError: If conversion fails.
    """
    try:
        user = User(
            id=int(payload["id"]),
            name=str(payload["name"]),
            level=int(payload["level"]),
            is_active=(str(payload.get("is_active", "true")).lower() != "false"),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid payload values for user creation") from exc
    return user


def validate_user(user: User) -> None:
    """Validate user access with early returns.

    Args:
        user: User to validate.

    Raises:
        PermissionError: If the user is inactive or lacks permission level.
    """
    if not user.is_active:
        raise PermissionError("Inactive user")

    if user.level < ADMIN_LEVEL_THRESHOLD:
        raise PermissionError(
            f"Insufficient permissions: level={user.level}, required={ADMIN_LEVEL_THRESHOLD}"
        )


def transform_items(items: Sequence[Item], *, min_value: float = 0.0) -> list[Item]:
    """Filter and transform items using readable loops instead of nested comprehensions.

    Applies a minimum value filter and normalizes negative tags.

    Args:
        items: Input item sequence.
        min_value: Minimum value threshold.

    Returns:
        A list of transformed items meeting the criteria.
    """
    transformed: list[Item] = []
    for item in items:
        # Guard clause: skip anything below threshold
        if item.value < min_value:
            continue
        # Example transformation: normalize tag to lowercase and strip
        normalized_tag = item.tag.strip().lower()
        transformed.append(Item(id=item.id, value=item.value, tag=normalized_tag))
    return transformed


def compute_metrics(items: Sequence[Item]) -> dict[str, float]:
    """Compute simple metrics from items.

    Uses explicit loops for clarity and to avoid deeply nested comprehensions.

    Args:
        items: Sequence of Item objects.

    Returns:
        A dictionary with count, total_value, and avg_value.
    """
    count = 0
    total_value = 0.0

    for item in items:
        count += 1
        total_value += float(item.value)

    avg_value = (total_value / count) if count else 0.0
    return {"count": float(count), "total_value": total_value, "avg_value": avg_value}


def format_response(user: User, metrics: Mapping[str, float]) -> dict[str, object]:
    """Format the response payload in a consistent structure.

    Args:
        user: The validated user.
        metrics: Computed metrics.

    Returns:
        A response dictionary suitable for JSON serialization.
    """
    return {
        "status": STATUS_PROCESSED,
        "user": {"id": user.id, "name": user.name, "level": user.level},
        "metrics": dict(metrics),
    }


# ------------------------------
# Orchestration entrypoint
# ------------------------------

def process_request(
    payload: Mapping[str, str],
    items_data: Sequence[Mapping[str, object]],
    *,
    min_value: float = 0.0,
) -> dict[str, object]:
    """End-to-end processing pipeline.

    This function demonstrates cohesive helper usage, early returns, and
    strengthened exception handling.

    Args:
        payload: Input mapping; must contain 'id', 'name', and 'level'.
        items_data: A sequence of mappings convertible to Item.
        min_value: Minimum value threshold for item filtering.

    Returns:
        A formatted response dictionary or an error payload.

    Raises:
        ValueError: For invalid inputs when not captured into an error payload.
    """
    try:
        normalized = parse_input(payload)
        user = _build_user(normalized)
        validate_user(user)
    except KeyError as err:
        logger.error("Missing required payload field: %s", err)
        return {"status": "error", "error": f"missing_field:{err}"}
    except PermissionError as err:
        logger.warning("Permission denied for user: %s", err)
        return {"status": "forbidden", "error": str(err)}
    except ValueError as err:
        logger.error("Invalid payload: %s", err)
        return {"status": "error", "error": str(err)}

    # Build items with explicit error handling
    items: list[Item] = []
    for idx, m in enumerate(items_data):
        try:
            item_id = int(m["id"])  # may raise KeyError/ValueError
            value = float(m["value"])  # may raise KeyError/ValueError
            tag = str(m.get("tag", ""))
        except KeyError as err:
            logger.debug("Skipping item %s due to missing key: %s", idx, err)
            continue
        except (TypeError, ValueError) as err:
            logger.debug("Skipping item %s due to bad value: %s", idx, err)
            continue
        items.append(Item(id=item_id, value=value, tag=tag))

    filtered = transform_items(items, min_value=min_value)
    metrics = compute_metrics(filtered)
    return format_response(user, metrics)


# ------------------------------
# Vectorized utilities (NumPy / Pandas)
# ------------------------------

def vectorized_calculation(a: np.ndarray, b: np.ndarray, c: float) -> np.ndarray:
    """Compute a * b + c in a vectorized fashion.

    Args:
        a: NumPy array.
        b: NumPy array, broadcast-compatible with a.
        c: Scalar to add.

    Returns:
        Vectorized result as a NumPy array.
    """
    return a * b + c


def compute_z_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add column 'z' equal to 'a' + 'b' using vectorization.

    Args:
        df: DataFrame with columns 'a' and 'b'.

    Returns:
        A copy of the DataFrame with the new 'z' column.

    Raises:
        KeyError: If required columns are missing.
    """
    if "a" not in df.columns or "b" not in df.columns:
        raise KeyError("DataFrame must contain 'a' and 'b' columns")
    out = df.copy()
    out["z"] = out["a"] + out["b"]
    return out


__all__ = [
    "ADMIN_LEVEL_THRESHOLD",
    "RETRY_LIMIT",
    "STATUS_PROCESSED",
    "User",
    "Item",
    "parse_input",
    "validate_user",
    "transform_items",
    "compute_metrics",
    "format_response",
    "process_request",
    "vectorized_calculation",
    "compute_z_column",
]