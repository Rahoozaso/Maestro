from typing import List


_WORD_TO_NUM = {
    'zero': 0,
    'one': 1,
    'two': 2,
    'three': 3,
    'four': 4,
    'five': 5,
    'six': 6,
    'seven': 7,
    'eight': 8,
    'nine': 9,
}
_NUM_TO_WORD = {v: k for k, v in _WORD_TO_NUM.items()}


def sort_numbers(numbers: str) -> str:
    """ Input is a space-delimited string of numberals from 'zero' to 'nine'.
    Valid choices are 'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight' and 'nine'.
    Return the string with numbers sorted from smallest to largest
    >>> sort_numbers('three one five')
    'one three five'
    """
    if not numbers:
        return ""
    words = numbers.split()
    try:
        sorted_nums = sorted(_WORD_TO_NUM[word] for word in words)
    except KeyError as e:
        raise ValueError(f"Invalid number word: {e.args[0]}") from None
    return " ".join(_NUM_TO_WORD[n] for n in sorted_nums)