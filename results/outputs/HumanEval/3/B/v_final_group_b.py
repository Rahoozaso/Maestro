from collections.abc import Iterable


def below_zero(operations: Iterable[int]) -> bool:
    """
    Determine whether a running account balance ever drops below zero.

    The account starts at zero; positive numbers are deposits and negative numbers are withdrawals.

    Examples:
    >>> below_zero([1, 2, 3])
    False
    >>> below_zero([1, 2, -4, 5])
    True
    """
    balance = 0
    for op in operations:
        balance += op
        if balance < 0:
            return True
    return False