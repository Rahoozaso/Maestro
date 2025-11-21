"""Statistical helpers for descriptive analytics.

This module currently provides a utility to compute the Mean Absolute
Deviation (MAD) around the arithmetic mean.
"""

from typing import List


def mean_absolute_deviation(numbers: List[float]) -> float:
    """Compute the mean absolute deviation (MAD) around the mean.

    MAD is the average absolute deviation from the arithmetic mean of the input.

    Args:
        numbers (list[float]): Sequence of numeric values.

    Returns:
        float: Mean absolute deviation around the mean. Returns 0.0 for empty input.

    Examples:
        >>> mean_absolute_deviation([1.0, 2.0, 3.0, 4.0])
        1.0
    """
    if not numbers:
        return 0.0
    mean = sum(numbers) / len(numbers)
    return sum(abs(x - mean) for x in numbers) / len(numbers)