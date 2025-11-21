def largest_divisor(n: int) -> int:
    """ For a given number n, find the largest number that divides n evenly, smaller than n
    >>> largest_divisor(15)
    5
    """
    if n <= 1:
        return 0
    # The first divisor >= 2 gives the largest proper divisor as n // i
    i = 2
    limit = int(n ** 0.5)
    while i <= limit:
        if n % i == 0:
            return n // i
        i += 1
    return 1