'''Utilities for computing maximum nesting depth for groups of parentheses.

This module exposes parse_nested_parens(), which takes a string of one or more
space-separated groups of parentheses and returns the maximum nesting depth for
each group.
'''

from typing import List


def parse_nested_parens(paren_string: str) -> List[int]:
    '''Return the maximum nesting depth of parentheses for each space-separated group.

    Args:
        paren_string: A string containing one or more groups of parentheses,
            separated by spaces. Example: '(()()) ((()))'.

    Returns:
        A list of integers where each element is the maximum nesting depth for
        the corresponding group in the input.

    Examples:
        >>> parse_nested_parens('(()()) ((())) () ((())()())')
        [2, 3, 1, 3]
    '''
    depths: List[int] = []
    for group in paren_string.split():
        current = 0
        maximum = 0
        for char in group:
            if char == '(':
                current += 1
                if current > maximum:
                    maximum = current
            elif char == ')':
                current -= 1
        depths.append(maximum)
    return depths