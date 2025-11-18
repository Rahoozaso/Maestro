def make_a_pile(n: int) -> list[int]:
    """
    Build a pile of stones with n levels.

    The first level has n stones. Each subsequent level increases by 2 stones,
    continuing the parity (odd/even) of the starting level.

    Parameters:
        n (int): Positive integer representing the number of levels.

    Returns:
        list[int]: List where index i contains the stone count for level i+1.

    Raises:
        TypeError: If n is not an int or is a bool.
        ValueError: If n <= 0.

    Examples:
    >>> make_a_pile(3)
    [3, 5, 7]
    >>> make_a_pile(4)
    [4, 6, 8, 10]
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer greater than 0.")
    if n <= 0:
        raise ValueError("n must be greater than 0.")

    return list(range(n, n + 2 * n, 2))