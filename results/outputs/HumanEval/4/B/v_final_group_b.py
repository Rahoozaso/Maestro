from typing import Iterable, SupportsFloat
import math


def mean_absolute_deviation(numbers: Iterable[SupportsFloat]) -> float:
    """Compute the mean absolute deviation around the mean for the given numbers.

    Returns 0.0 for an empty iterable.

    MAD = average(|x - mean|)

    >>> mean_absolute_deviation([1.0, 2.0, 3.0, 4.0])
    1.0
    """
    seq = tuple(float(x) for x in numbers)
    n = len(seq)
    if n == 0:
        return 0.0
    mean = math.fsum(seq) / n
    return math.fsum(abs(x - mean) for x in seq) / n