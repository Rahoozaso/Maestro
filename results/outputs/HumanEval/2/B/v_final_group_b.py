import math

def truncate_number(number: float) -> float:
    """Return the fractional part of a finite real number in [0.0, 1.0).

    For negative inputs, this returns x - floor(x).

    >>> truncate_number(3.5)
    0.5
    """
    if not math.isfinite(number):
        raise ValueError("number must be finite")

    return number - math.floor(number)