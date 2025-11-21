def is_prime(x: int) -> bool:
    if x < 2:
        return False
    if x % 2 == 0:
        return x == 2
    if x % 3 == 0:
        return x == 3
    i = 5
    step = 2
    while i * i <= x:
        if x % i == 0:
            return False
        i += step
        step = 6 - step
    return True


def prime_fib(n: int):
    """
    prime_fib returns n-th number that is a Fibonacci number and it's also prime.
    >>> prime_fib(1)
    2
    >>> prime_fib(2)
    3
    >>> prime_fib(3)
    5
    >>> prime_fib(4)
    13
    >>> prime_fib(5)
    89
    """
    if n < 1:
        raise ValueError("n must be a positive integer")

    a, b = 1, 1  # Fibonacci sequence starting values
    count = 0
    while True:
        a, b = b, a + b  # advance to next Fibonacci number (a is current)
        if is_prime(a):
            count += 1
            if count == n:
                return a