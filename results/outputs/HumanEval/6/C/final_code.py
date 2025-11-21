from typing import List


def parse_nested_parens(paren_string: str) -> List[int]:
    """ Input to this function is a string represented multiple groups for nested parentheses separated by spaces.
    For each of the group, output the deepest level of nesting of parentheses.
    E.g. (()()) has maximum two levels of nesting while ((())) has three.

    >>> parse_nested_parens('(()()) ((())) () ((())()())')
    [2, 3, 1, 3]
    """
    depths: List[int] = []
    for group in paren_string.split():
        current = 0
        maximum = 0
        for ch in group:
            if ch == '(':
                current += 1
                if current > maximum:
                    maximum = current
            elif ch == ')':
                current -= 1
        depths.append(maximum)
    return depths