"""
Palindrome utilities: test and construct palindromes.

This module provides:
- is_palindrome(string): Determine if the given text reads the same forwards and backwards.
- make_palindrome(string): Produce the shortest palindrome that begins with the given text.

Both functions are pure (no side effects).
"""

def is_palindrome(string: str) -> bool:
    """Return True if 'string' is a palindrome.

    Args:
        string: The input text to evaluate.

    Returns:
        True if string equals its reverse; otherwise, False.

    Examples:
        >>> is_palindrome('abba')
        True
        >>> is_palindrome('abc')
        False
    """
    return string == string[::-1]


def make_palindrome(string: str) -> str:
    """Return the shortest palindrome that begins with 'string'.

    Algorithm:
    - Find the longest palindromic suffix of the supplied string.
    - Append to the end of the string the reverse of the prefix that precedes that suffix.

    Args:
        string: The starting text.

    Returns:
        A palindrome whose prefix equals the original string.

    Examples:
        >>> make_palindrome('')
        ''
        >>> make_palindrome('cat')
        'catac'
        >>> make_palindrome('cata')
        'catac'
    """
    for i in range(len(string) + 1):
        if is_palindrome(string[i:]):
            return string + string[:i][::-1]
    # Fallback (should never reach here because empty suffix is a palindrome)
    return string