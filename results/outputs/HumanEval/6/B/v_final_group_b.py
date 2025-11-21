from typing import List


def parse_nested_parens(paren_string: str) -> List[int]:
    """Return the maximum nesting depth for each space-separated group of parentheses.

    For example:
        '(()()) ((())) () ((())()())' -> [2, 3, 1, 3]

    Raises:
        TypeError: If paren_string is not a str.
        ValueError: If a group contains characters other than '(' or ')',
                    or if the parentheses in a group are unbalanced.
    """
    if not isinstance(paren_string, str):
        raise TypeError("paren_string must be a str")

    depths: List[int] = []
    for idx, group in enumerate(paren_string.split()):
        current = 0
        maximum = 0
        for pos, ch in enumerate(group):
            if ch == '(':
                current += 1
                if current > maximum:
                    maximum = current
            elif ch == ')':
                current -= 1
                if current < 0:
                    raise ValueError(
                        f"Unbalanced parentheses in group {idx}: "
                        f"closing paren without matching opening at position {pos}"
                    )
            else:
                raise ValueError(
                    f"Invalid character {ch!r} in group {idx} at position {pos}; "
                    "only '(' and ')' are allowed"
                )
        if current != 0:
            raise ValueError(
                f"Unbalanced parentheses in group {idx}: "
                f"{current} more opening than closing parentheses"
            )
        depths.append(maximum)
    return depths