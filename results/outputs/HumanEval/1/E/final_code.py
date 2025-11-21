from typing import List


def separate_paren_groups(paren_string: str) -> List[str]:
    """ Input to this function is a string containing multiple groups of nested parentheses. Your goal is to
    separate those group into separate strings and return the list of those.
    Separate groups are balanced (each open brace is properly closed) and not nested within each other
    Ignore any spaces in the input string.
    >>> separate_paren_groups('( ) (( )) (( )( ))')
    ['()', '(())', '(()())']
    """
    res: List[str] = []
    current: list[str] = []
    depth = 0

    for ch in paren_string:
        if ch == ' ':
            continue
        if ch not in ('(', ')'):
            continue  # ignore any non-parenthesis characters
        current.append(ch)
        if ch == '(':
            depth += 1
        else:  # ch == ')'
            depth -= 1

        if depth == 0 and current:
            res.append(''.join(current))
            current = []

    return res