"""
Utilities for detecting whether a numeric collection contains two elements that are
closer than a specified threshold.

This module favors readability: small, single-purpose helpers, early-return guard
clauses, and clear, precise typing.
"""

from typing import List, Sequence

# Named constants to avoid magic numbers in the code
MIN_REQUIRED_NUMBERS = 2


def sort_numbers(numbers: Sequence[float]) -> List[float]:
    """Return a new list with the numbers sorted in ascending order.

    Args:
        numbers: A finite sequence of float values.

    Returns:
        A new list containing the sorted numbers.
    """
    return sorted(numbers)


def any_adjacent_within_threshold(sorted_numbers: Sequence[float], threshold: float) -> bool:
    """Check if any adjacent pair in a sorted sequence differs by less than threshold.

    Args:
        sorted_numbers: Numbers sorted in ascending order.
        threshold: A positive float threshold.

    Returns:
        True if any adjacent pair has absolute difference strictly less than threshold;
        False otherwise.
    """
    for a, b in zip(sorted_numbers, sorted_numbers[1:]):
        if abs(a - b) < threshold:
            return True
    return False


def has_close_elements(numbers: Sequence[float], threshold: float) -> bool:
    """Check whether any two numbers in the input are closer than the given threshold.

    Args:
        numbers: A sequence of float values.
        threshold: A positive float threshold.

    Returns:
        True if there exist two elements with absolute difference strictly less than
        threshold; False otherwise.

    Examples:
        >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
        False
        >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
        True
    """
    # Guard clauses (early returns) for invalid or trivial cases
    if len(numbers) < MIN_REQUIRED_NUMBERS:
        return False
    if threshold <= 0:
        return False

    sorted_nums = sort_numbers(numbers)
    return any_adjacent_within_threshold(sorted_nums, threshold)