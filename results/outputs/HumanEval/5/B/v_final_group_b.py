from typing import Iterable, List, TypeVar

T = TypeVar("T")


def intersperse(numbers: Iterable[T], delimiter: T) -> List[T]:
    """Insert a value 'delimiter' between every two consecutive elements of `numbers`.

    Examples:
    >>> intersperse([], 4)
    []
    >>> intersperse([1, 2, 3], 4)
    [1, 4, 2, 4, 3]
    """
    it = iter(numbers)
    try:
        first = next(it)
    except StopIteration:
        return []
    result: List[T] = [first]
    append = result.append
    for num in it:
        append(delimiter)
        append(num)
    return result