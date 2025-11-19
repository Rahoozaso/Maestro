from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "process_data",
    "frequency_counts",
    "tokenize_with_regex",
    "safe_divide",
    "compute_metrics",
]


def is_valid_data(data: Optional[Iterable[Any]]) -> bool:
    """Guard: verify data is a non-empty iterable.

    Uses early return semantics at call sites to flatten control flow.
    """
    if data is None:
        return False
    # Allow sequences and generic iterables; ensure non-empty where possible.
    try:
        # Try cheap emptiness check for sequences
        if isinstance(data, Sequence):
            return len(data) > 0
    except Exception:
        # Fall back to truthiness for non-sized iterables (best-effort)
        pass
    # For generic iterables, attempt to peek
    try:
        iterator = iter(data)  # type: ignore[arg-type]
    except TypeError:
        return False
    try:
        first = next(iterator)
    except StopIteration:
        return False
    # Reconstruct an iterator including the first item if needed
    # Caller should not rely on the original iterable consumption in this helper.
    return True


def process_data(data: Optional[Iterable[int]]) -> Optional[List[int]]:
    """Process a stream of integers, demonstrating flattened control flow.

    - Early-return if preconditions fail (None or invalid data).
    - Split logic into small, descriptive helpers when needed.
    """
    if not is_valid_data(data):
        return None

    # At this point, data is considered valid. Convert to a list for idempotent use.
    items = list(data)  # type: ignore[arg-type]
    if not items:
        return None

    # Example transformation: keep even squares only.
    return [x * x for x in items if x % 2 == 0]


def frequency_counts(items: Iterable[Any]) -> Dict[Any, int]:
    """Compute frequency counts efficiently using collections.Counter.

    This replaces nested loops or repeated summations with an O(n) solution.
    """
    # Before (inefficient):
    # counts = {}
    # for x in items:
    #     counts[x] = sum(1 for y in items if y == x)

    # After (efficient):
    counts = Counter(items)

    # If a plain dict is preferred:
    # counts = {}
    # for x in items:
    #     counts[x] = counts.get(x, 0) + 1

    return dict(counts)


def tokenize_with_regex(text: str, pattern: str) -> List[str]:
    """Tokenize text using a regex pattern with a lazy import.

    The 're' module is imported lazily because it is only used here,
    reducing startup overhead and keeping global namespace minimal.
    """
    import re  # Lazy and specific import within the function scope

    return re.findall(pattern, text)


def safe_divide(a: float, b: float) -> Optional[float]:
    """Example of early returns (guard clauses) for control-flow flattening."""
    if b == 0:
        return None
    return a / b


def compute_metrics(points: Iterable[Tuple[float, float]]) -> Optional[float]:
    """Compute an aggregate metric over 2D points.

    Demonstrates:
    - Early returns for invalid inputs.
    - Local binding of functions to speed attribute access in tight loops.

    Returns the sum of Euclidean norms of the input points, or None if invalid.
    """
    if not is_valid_data(points):
        return None

    # Local binding example for speed in tight loops:
    # from math import sqrt  # faster local binding than math.sqrt in tight loops
    from math import sqrt  # intentionally local for attribute access speed-up

    total = 0.0
    for (x, y) in points:
        total += sqrt(x * x + y * y)
    return total