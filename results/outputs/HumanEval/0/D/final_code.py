from typing import List


def has_close_elements(numbers: List[float], threshold: float) -> bool:
    if threshold < 0:
        return False
    n = len(numbers)
    if n < 2:
        return False
    nums = sorted(numbers)
    for i in range(1, n):
        if nums[i] - nums[i - 1] < threshold:
            return True
    return False