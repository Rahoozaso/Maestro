from typing import List


def factorize(n: int) -> List[int]:
    """ Return list of prime factors of given integer in the order from smallest to largest.
    Each of the factors should be listed number of times corresponding to how many times it appeares in factorization.
    Input number should be equal to the product of all factors
    >>> factorize(8)
    [2, 2, 2]
    >>> factorize(25)
    [5, 5]
    >>> factorize(70)
    [2, 5, 7]
    """
    factors: List[int] = []
    if n < 2:
        return factors

    # Factor out 2s
    while n % 2 == 0:
        factors.append(2)
        n //= 2

    # Factor out odd primes
    i = 3
    while i * i <= n:
        while n % i == 0:
            factors.append(i)
            n //= i
        i += 2

    # If remainder is a prime > 1
    if n > 1:
        factors.append(n)

    return factors