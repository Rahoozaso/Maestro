def how_many_times(string: str, substring: str) -> int:
    """ Find how many times a given substring can be found in the original string. Count overlaping cases.
    >>> how_many_times('', 'a')
    0
    >>> how_many_times('aaa', 'a')
    3
    >>> how_many_times('aaaa', 'aa')
    3
    """
    if not substring:
        return 0
    count = 0
    m = len(substring)
    for i in range(0, len(string) - m + 1):
        if string[i:i + m] == substring:
            count += 1
    return count