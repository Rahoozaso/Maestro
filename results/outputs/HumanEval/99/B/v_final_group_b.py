from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def closest_integer(value: str) -> int:
    '''
    Create a function that takes a value (string) representing a number
    and returns the closest integer to it. If the number is equidistant
    from two integers, round it away from zero.

    Examples
    >>> closest_integer("10")
    10
    >>> closest_integer("15.3")
    15

    Note:
    Rounding away from zero means that if the given number is equidistant
    from two integers, the one you should return is the one that is the
    farthest from zero. For example closest_integer("14.5") should
    return 15 and closest_integer("-14.5") should return -15.
    '''
    s = value.strip() if isinstance(value, str) else str(value).strip()

    # Fast path for plain decimal integers
    try:
        return int(s)
    except ValueError:
        pass

    try:
        d = Decimal(s)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid numeric input: {value!r}") from None

    if not d.is_finite():
        raise ValueError(f"Non-finite numeric input: {value!r}")

    return int(d.to_integral_value(rounding=ROUND_HALF_UP))