from typing import List


def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """
    Return True if any two numbers in the list are closer to each other than the given threshold.

    This implementation sorts a copy of the list (O(n log n)) and compares only adjacent pairs,
    which is sufficient because the smallest difference must occur between neighbors in the sorted order.

    Edge cases:
    - threshold <= 0: always returns False (strictly "closer than" comparison).
    - Lists with fewer than 2 elements: returns False.

    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
    True
    """
    if threshold <= 0 or len(numbers) < 2:
        return False

    sorted_nums = sorted(numbers)
    # Since the list is sorted, the minimal absolute difference appears between neighbors.
    for i in range(1, len(sorted_nums)):
        # Neighbor differences are non-negative; no need for abs().
        if (sorted_nums[i] - sorted_nums[i - 1]) < threshold:
            return True
    return False