def separate_paren_groups(paren_string: str) -> list[str]:
    """
    Split a string containing multiple groups of nested parentheses into separate balanced groups.

    - Ignores any non-parenthesis characters.
    - Raises ValueError if the parentheses are unbalanced.

    Example:
    >>> separate_paren_groups('( ) (( )) (( )( ))')
    ['()', '(())', '(()())']
    """
    result: list[str] = []
    current: list[str] = []
    depth = 0

    for idx, ch in enumerate(paren_string):
        if ch not in '()':
            continue

        current.append(ch)
        if ch == '(':
            depth += 1
        else:  # ch == ')'
            depth -= 1
            if depth < 0:
                raise ValueError(f"Unbalanced parentheses: extra ')' at position {idx}")

        if depth == 0:
            result.append(''.join(current))
            current.clear()

    if depth != 0:
        raise ValueError("Unbalanced parentheses: missing ')' to close some group(s)")

    return result