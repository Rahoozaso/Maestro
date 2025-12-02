from typing import Iterable, Callable, Any
from io import StringIO
from math import sqrt


def accumulate_chunks_join(chunks: Iterable[str]) -> str:
    """Accumulate string chunks efficiently using ''.join().

    This avoids quadratic-time string concatenation in a loop.
    """
    parts: list[str] = []
    append = parts.append
    for chunk in chunks:
        append(chunk)
    return ''.join(parts)


def accumulate_chunks_stringio(chunks: Iterable[str]) -> str:
    """Accumulate string chunks efficiently using io.StringIO for very large outputs."""
    buf = StringIO()
    write = buf.write
    for chunk in chunks:
        write(chunk)
    return buf.getvalue()


# Lazy import inside the function that needs it
# Using specific symbol import (sqrt) to reduce attribute access overhead

def compute_svd(x: Any):
    """Compute SVD with a deferred NumPy import to avoid import overhead unless needed."""
    import numpy as np  # deferred, only if called
    return np.linalg.svd(x, full_matrices=False)


def distance(dx: float, dy: float) -> float:
    """Example usage of a specific symbol import to reduce attribute lookups."""
    return sqrt(dx * dx + dy * dy)


# Iterative DFS to replace deep recursion, avoiding recursion overhead/overflow

def dfs_iter(root: Any, visit: Callable[[Any], None]) -> None:
    """Depth-first traversal using an explicit stack.

    The order matches a typical recursive DFS if children are pushed in reverse.
    The nodes are expected to have a "children" iterable attribute; if missing,
    they are treated as leaves.
    """
    if root is None:
        return
    stack: list[Any] = [root]
    while stack:
        node = stack.pop()
        visit(node)
        children = getattr(node, 'children', [])
        for child in reversed(list(children)):
            stack.append(child)