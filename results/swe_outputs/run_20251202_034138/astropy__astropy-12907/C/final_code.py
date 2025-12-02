from __future__ import annotations

from typing import List


def separability_matrix_for_nested_compound(n_inputs: int, n_outputs: int) -> List[List[bool]]:
    """Return a separability matrix treating each input as independent.

    This is a minimal stand‑in helper illustrating how a correct separability
    matrix should look for a fully separable model with ``n_inputs`` inputs
    and ``n_outputs`` outputs. The matrix is ``(n_outputs, n_inputs)`` where
    element ``[i][j]`` is ``True`` iff output ``i`` depends on input ``j``.

    Parameters
    ----------
    n_inputs : int
        Total number of input coordinates to the overall model.
    n_outputs : int
        Total number of output coordinates from the overall model.

    Returns
    -------
    List[List[bool]]
        A boolean matrix with ``True`` on the diagonal and ``False``
        elsewhere.
    """

    if n_inputs <= 0:
        raise ValueError("n_inputs must be positive")
    if n_outputs <= 0:
        raise ValueError("n_outputs must be positive")

    size = max(n_inputs, n_outputs)

    matrix: List[List[bool]] = []
    for out_idx in range(size):
        row: List[bool] = []
        for in_idx in range(size):
            row.append(out_idx == in_idx)
        matrix.append(row)

    # Truncate to the exact (n_outputs, n_inputs) shape
    return [row[:n_inputs] for row in matrix[:n_outputs]]