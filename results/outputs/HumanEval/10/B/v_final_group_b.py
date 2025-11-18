from typing import List


def is_palindrome(string: str) -> bool:
    """Return True if the given string is a palindrome, else False."""
    if not isinstance(string, str):
        raise TypeError("is_palindrome expects a 'str'")
    return string == string[::-1]


def _prefix_function(s: str) -> List[int]:
    """Compute KMP prefix-function (pi) array for string s."""
    pi = [0] * len(s)
    for i in range(1, len(s)):
        j = pi[i - 1]
        while j > 0 and s[i] != s[j]:
            j = pi[j - 1]
        if s[i] == s[j]:
            j += 1
        pi[i] = j
    return pi


def _pick_sentinel(s: str) -> str:
    """Pick a delimiter character that does not occur in s."""
    candidates = ['\u0000', '\u0001', '\u0002', '\u001F', '\uE000', '\uF8FF', '\uFFFE', '\uFFFF']
    for c in candidates:
        if c not in s:
            return c
    used = set(s)
    # Fallback (practically never reached)
    for code in range(0x110000):
        ch = chr(code)
        if ch not in used:
            return ch
    raise ValueError("Unable to find a sentinel character not present in input.")


def make_palindrome(string: str) -> str:
    """
    Find the shortest palindrome that begins with the supplied string by appending the
    minimum number of characters to its end.

    Approach:
    - Compute the longest palindromic suffix of the string in O(n) using KMP over
      reversed(string) + sentinel + string.
    - Append the reverse of the remaining prefix.

    >>> make_palindrome('')
    ''
    >>> make_palindrome('cat')
    'catac'
    >>> make_palindrome('cata')
    'catac'
    """
    if not isinstance(string, str):
        raise TypeError("make_palindrome expects a 'str'")
    if not string:
        return string

    rev = string[::-1]
    sep = _pick_sentinel(string)  # ensure the delimiter cannot match across segments
    combined = rev + sep + string
    k = _prefix_function(combined)[-1]  # length of the longest palindromic suffix
    return string + string[:len(string) - k][::-1]