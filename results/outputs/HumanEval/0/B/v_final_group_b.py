from typing import Sequence


def has_close_elements(numbers: Sequence[float], threshold: float) -> bool:
    """Return True if any two numbers are closer than the given positive threshold.

    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
    True
    """
    if threshold <= 0:
        return False

    n = len(numbers)
    if n < 2:
        return False

    sorted_nums = sorted(numbers)
    prev = sorted_nums[0]
    for i in range(1, n):
        current = sorted_nums[i]
        if current - prev < threshold:
            return True
        prev = current
    return False