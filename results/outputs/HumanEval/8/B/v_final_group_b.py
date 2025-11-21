from math import prod
from typing import List, Tuple


def sum_product(numbers: List[int]) -> Tuple[int, int]:
    """
    For a given list of integers, return a tuple consisting of the sum and the product of all
    the integers in the list. Empty sum is 0 and empty product is 1.

    >>> sum_product([])
    (0, 1)
    >>> sum_product([1, 2, 3, 4])
    (10, 24)
    """
    # Built-in implementations are optimized in C and are faster than a Python loop.
    return sum(numbers), prod(numbers, start=1)