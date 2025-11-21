from typing import Final


def is_palindrome(s: str) -> bool:
    """Return True if s is a palindrome (compares characters without extra allocations)."""
    if not isinstance(s, str):
        raise TypeError("is_palindrome expects a str")
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True


def _longest_palindromic_suffix_length(s: str) -> int:
    """
    Compute the length of the longest palindromic suffix of s using Manacher's algorithm.
    Runs in O(n) time and O(n) space.
    """
    n: Final[int] = len(s)
    if n == 0:
        return 0

    # d1[i] = radius for odd-length palindromes centered at i
    d1 = [0] * n
    l = 0
    r = -1
    for i in range(n):
        k = 1 if i > r else min(d1[l + r - i], r - i + 1)
        while i - k >= 0 and i + k < n and s[i - k] == s[i + k]:
            k += 1
        d1[i] = k
        if i + k - 1 > r:
            l = i - k + 1
            r = i + k - 1

    # d2[i] = radius for even-length palindromes centered between i-1 and i
    d2 = [0] * n
    l = 0
    r = -1
    for i in range(n):
        k = 0 if i > r else min(d2[l + r - i + 1], r - i + 1)
        while i - k - 1 >= 0 and i + k < n and s[i - k - 1] == s[i + k]:
            k += 1
        d2[i] = k
        if i + k - 1 > r:
            l = i - k
            r = i + k - 1

    best = 0
    # Palindromes ending at the last index (n-1)
    for i in range(n):
        # odd end index = i + d1[i] - 1
        if i + d1[i] - 1 == n - 1:
            best = max(best, 2 * d1[i] - 1)
        # even end index = i + d2[i] - 1
        if i + d2[i] - 1 == n - 1:
            best = max(best, 2 * d2[i])

    return best


def make_palindrome(s: str) -> str:
    """
    Return the shortest palindrome that begins with the supplied string s.
    The result is formed by appending the reverse of the minimal prefix
    required to make the whole string a palindrome.

    Examples:
    >>> make_palindrome('')
    ''
    >>> make_palindrome('cat')
    'catac'
    >>> make_palindrome('cata')
    'catac'
    """
    if not isinstance(s, str):
        raise TypeError("make_palindrome expects a str")

    n = len(s)
    if n < 2 or is_palindrome(s):
        return s

    pal_suffix_len = _longest_palindromic_suffix_length(s)
    # Append reverse of the non-palindromic prefix
    return s + s[: n - pal_suffix_len][::-1]