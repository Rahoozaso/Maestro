from typing import Iterable, List


def filter_by_substring(strings: Iterable[str], substring: str) -> List[str]:
    """Return a list containing only the strings that include the given substring.

    The check is case-sensitive and treats an empty substring as matching all strings.

    Examples:
        >>> filter_by_substring([], 'a')
        []
        >>> filter_by_substring(['abc', 'bacd', 'cde', 'array'], 'a')
        ['abc', 'bacd', 'array']

    Args:
        strings: An iterable of strings to filter.
        substring: The substring to search for.

    Returns:
        A new list containing only the items from 'strings' that contain 'substring'.

    Raises:
        TypeError: If 'substring' is not a str, or any element in 'strings' is not a str.
    """
    if not isinstance(substring, str):
        raise TypeError(f"substring must be str, got {type(substring).__name__}")

    result: List[str] = []

    # Fast-path for empty substring: all strings match (after validation).
    if substring == "":
        for idx, s in enumerate(strings):
            if not isinstance(s, str):
                raise TypeError(f"strings[{idx}] must be str, got {type(s).__name__}")
            result.append(s)
        return result

    for idx, s in enumerate(strings):
        if not isinstance(s, str):
            raise TypeError(f"strings[{idx}] must be str, got {type(s).__name__}")
        if substring in s:
            result.append(s)
    return result