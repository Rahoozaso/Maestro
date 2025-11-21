"""
String filtering utilities.

This module provides helpers to filter a list of strings based on the presence of a substring.

Example:
>>> filter_by_substring(['abc', 'bacd', 'cde', 'array'], 'a')
['abc', 'bacd', 'array']
"""

from typing import List


def _validate_input(strings: List[str], substring: str) -> None:
    """Validate the inputs for the filtering operation.

    Ensures that `strings` is a list of strings and `substring` is a string.
    """
    if not isinstance(strings, list):
        raise TypeError("strings must be a list of str")
    if not isinstance(substring, str):
        raise TypeError("substring must be a str")
    for idx, s in enumerate(strings):
        if not isinstance(s, str):
            raise TypeError(f"strings[{idx}] must be a str, got {type(s).__name__}")


def _contains_substring(s: str, substring: str) -> bool:
    """Return True if substring is found within s."""
    return substring in s


def filter_by_substring(strings: List[str], substring: str) -> List[str]:
    """ Filter an input list of strings only for ones that contain given substring
    >>> filter_by_substring([], 'a')
    []
    >>> filter_by_substring(['abc', 'bacd', 'cde', 'array'], 'a')
    ['abc', 'bacd', 'array']
    """
    _validate_input(strings, substring)
    return [s for s in strings if _contains_substring(s, substring)]