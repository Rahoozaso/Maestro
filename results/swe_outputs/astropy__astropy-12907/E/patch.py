from __future__ import annotations

import numpy as np
from typing import Any

__all__ = ["separability_matrix"]


def separability_matrix(model: Any) -> np.ndarray:
    """
    Compute a boolean matrix M of shape (n_outputs, n_inputs) where
    M[i, j] is True if output i depends on input j.

    This implementation correctly handles nested CompoundModels by using:
      - block-diagonal composition for parallel combination ('&')
      - boolean matrix multiplication for serial composition ('|')
      - per-output union of dependencies for element-wise binary ops ('+', '-', '*', etc.)

    For non-compound base models, conservatively assume each output depends on all inputs
    (a full True matrix of shape (n_outputs, n_inputs)).
    """

    def _is_compound(m: Any) -> bool:
        # Avoid importing CompoundModel directly to prevent circular deps
        return hasattr(m, "op") and hasattr(m, "left") and hasattr(m, "right")

    def _block_diag(A: np.ndarray, B: np.ndarray) -> np.ndarray:
        out = np.zeros((A.shape[0] + B.shape[0], A.shape[1] + B.shape[1]), dtype=bool)
        out[: A.shape[0], : A.shape[1]] = A
        out[A.shape[0] :, A.shape[1] :] = B
        return out

    def _bool_matmul(R: np.ndarray, L: np.ndarray) -> np.ndarray:
        # Boolean composition: (R ∘ L). Shapes: R: (o_r, i_r), L: (o_l, i_l) with i_r == o_l
        # Use integer matmul and threshold to compute boolean reachability.
        return (R.astype(np.uint8) @ L.astype(np.uint8)) > 0

    if _is_compound(model):
        Lm = separability_matrix(model.left)
        Rm = separability_matrix(model.right)
        op = model.op

        if op == "&":
            # Parallel composition: inputs/outputs concatenate; block-diagonal matrix
            return _block_diag(Lm, Rm)
        elif op == "|":
            # Serial composition: right after left; boolean matrix multiplication
            return _bool_matmul(Rm, Lm)
        else:
            # Element-wise binary ops (+, -, *, /, etc.)
            # If both sides produce the same number of outputs, the resulting
            # dependencies per output are the union of their dependencies and
            # the inputs concatenate.
            if Lm.shape[0] == Rm.shape[0]:
                left_ext = np.hstack(
                    [Lm, np.zeros((Lm.shape[0], Rm.shape[1]), dtype=bool)]
                )
                right_ext = np.hstack(
                    [np.zeros((Rm.shape[0], Lm.shape[1]), dtype=bool), Rm]
                )
                return np.logical_or(left_ext, right_ext)
            # Fallback: if outputs differ, treat as parallel in the dependency sense
            return _block_diag(Lm, Rm)
    else:
        # Base model: conservatively assume each output depends on all inputs
        return np.ones((model.n_outputs, model.n_inputs), dtype=bool)