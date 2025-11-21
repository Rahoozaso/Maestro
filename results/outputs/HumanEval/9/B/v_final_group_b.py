from typing import Iterable, List, Optional


def rolling_max(numbers: Iterable[int]) -> List[int]:
    """From an iterable of integers, return a list of running maxima.
    >>> rolling_max([1, 2, 3, 2, 3, 4, 2])
    [1, 2, 3, 3, 3, 4, 4]
    """
    result: List[int] = []
    max_so_far: Optional[int] = None
    append = result.append  # micro-optimization to avoid attribute lookup in loop
    for num in numbers:
        if max_so_far is None or num > max_so_far:
            max_so_far = num
        append(max_so_far)
    return result