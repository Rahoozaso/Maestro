"""Sequence utilities.

This module provides a utility to insert a delimiter between consecutive
elements of a list of integers.
"""
from typing import List


def intersperse(numbers: List[int], delimiter: int) -> List[int]:
    """Insert a delimiter between every two consecutive elements of numbers.

    Args:
        numbers: The input list of integers.
        delimiter: The integer to insert between elements.

    Returns:
        A new list with the delimiter interleaved between original elements.

    Examples:
        >>> intersperse([], 4)
        []
        >>> intersperse([1, 2, 3], 4)
        [1, 4, 2, 4, 3]
    """
    if not numbers:
        return []

    result: List[int] = []
    for index, value in enumerate(numbers):
        if index > 0:
            result.append(delimiter)
        result.append(value)
    return result