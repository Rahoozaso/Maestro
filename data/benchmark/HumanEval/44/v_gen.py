def change_base(x: int, base: int):
    """Change numerical base of input number x to base.
    return string representation after the conversion.
    base numbers are less than 10.
    >>> change_base(8, 3)
    '22'
    >>> change_base(8, 2)
    '1000'
    >>> change_base(7, 2)
    '111'
    """
    if not isinstance(x, int) or not isinstance(base, int):
        raise TypeError("x and base must be integers")
    if base < 2 or base > 9:
        raise ValueError("base must be between 2 and 9 inclusive")

    if x == 0:
        return "0"

    negative = x < 0
    n = -x if negative else x
    digits = []

    while n > 0:
        digits.append(str(n % base))
        n //= base

    result = ''.join(reversed(digits))
    return '-' + result if negative else result