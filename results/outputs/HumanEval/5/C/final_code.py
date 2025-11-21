"""Utility for interspersing a delimiter between elements of a list.

This module provides a single function, intersperse, which inserts a given
integer delimiter between every pair of consecutive integers in the input list.
It is implemented efficiently with early returns and slice assignments.
"""

from typing import List


def intersperse(numbers: List[int], delimeter: int) -> List[int]:
    """Insert a number between every two consecutive elements of a list.

    Args:
        numbers: A list of integers to be interspersed.
        delimeter: The integer value to insert between consecutive elements
            of ``numbers``. Note: The parameter is spelled "delimeter" in the
            function signature to preserve the existing API.

    Returns:
        A new list of integers where ``delimeter`` is inserted between every
        two consecutive elements of ``numbers``. If ``numbers`` is empty, an
        empty list is returned.

    Examples:
        >>> intersperse([], 4)
        []
        >>> intersperse([1, 2, 3], 4)
        [1, 4, 2, 4, 3]
    """
    # Guard clause for trivial case to avoid unnecessary work
    if not numbers:
        return []

    # Efficient construction via pre-allocation and slice assignment
    result: List[int] = [0] * (len(numbers) * 2 - 1)
    result[::2] = numbers
    result[1::2] = [delimeter] * (len(numbers) - 1)
    return result