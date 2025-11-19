from __future__ import annotations

import numpy as np
from typing import Any

__all__ = ["separability_matrix"]


def _bool_block_diag(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Boolean block-diagonal combination of two matrices.

    Given two boolean dependency matrices A and B (each of shape
    (n_outputs, n_inputs)), this returns a block-diagonal matrix of shape
    ((A.shape[0] + B.shape[0]), (A.shape[1] + B.shape[1])) with A in the
    top-left block and B in the bottom-right block, and False elsewhere.
    """
    if A.dtype != bool or B.dtype != bool:
        raise TypeError("_bool_block_diag expects boolean dtype arrays")
    a_out, a_in = A.shape
    b_out, b_in = B.shape
    out = np.zeros((a_out + b_out, a_in + b_in), dtype=bool)
    out[:a_out, :a_in] = A
    out[a_out:, a_in:] = B
    return out


def _bool_matmul(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Boolean matrix multiplication.

    Computes C where C[i, j] = OR_k (A[i, k] AND B[k, j]).

    Both A and B must be boolean arrays with compatible inner dimensions.
    """
    if A.dtype != bool or B.dtype != bool:
        raise TypeError("_bool_matmul expects boolean dtype arrays")
    if A.shape[1] != B.shape[0]:
        raise ValueError(
            f"Inner dimensions must match for boolean matmul: {A.shape} x {B.shape}"
        )
    # Vectorized boolean matmul: (i,k) & (k,j) reduced over k
    return (A[..., :, None] & B[..., None, :]).any(axis=-1)


def _all_true_matrix(n_out: int, n_in: int) -> np.ndarray:
    """Construct a conservative all-True dependency matrix of given shape."""
    return np.ones((n_out, n_in), dtype=bool)


def separability_matrix(model: Any) -> np.ndarray:
    """Compute the separability (dependency) matrix of a model.

    This function returns a boolean matrix M of shape (n_outputs, n_inputs)
    indicating whether output i depends on input j (True = depends, False =
    independent). The evaluation proceeds recursively for compound models
    and preserves the internal separability structure of nested submodels.

    Combination rules for CompoundModels:
    - Parallel ('&'): The separability matrix is a block-diagonal assembly of
      the left and right submodel matrices, reflecting independent branches.
    - Composition ('|'): The matrix is composed via boolean matrix
      multiplication, propagating dependencies from the right submodel back to
      the original inputs through the left submodel.

    Nested CompoundModels are recursively evaluated such that the internal
    separability structure of submodels is preserved and not treated as an
    opaque block.

    For non-compound (leaf) models, the conservative assumption is that each
    output may depend on every input, resulting in an all-True matrix of shape
    (n_outputs, n_inputs). This preserves correctness; compound structure then
    refines independence through the combination rules above.

    Parameters
    ----------
    model : Model
        An astropy model or a compound model built from models.

    Returns
    -------
    numpy.ndarray
        A boolean array of shape (n_outputs, n_inputs) encoding dependencies.
    """
    # Duck-typing for CompoundModel: expect attributes 'op', 'left', 'right'.
    try:
        op = getattr(model, "op")
        left = getattr(model, "left")
        right = getattr(model, "right")
        has_compound_shape = True
    except Exception:
        has_compound_shape = False

    if has_compound_shape and op is not None and left is not None and right is not None:
        left_m = separability_matrix(left)
        right_m = separability_matrix(right)

        if op == "&":
            # Parallel branches: block-diagonal combination.
            return _bool_block_diag(left_m, right_m)
        elif op == "|":
            # Composition: outputs of right depend on outputs of left, propagate
            # back to original inputs via boolean matmul.
            # If left maps inputs -> mid, and right maps mid -> outputs,
            # left_m shape: (mid, inputs), right_m shape: (outputs, mid)
            # result shape: (outputs, inputs) = right_m @ left_m (boolean)
            return _bool_matmul(right_m, left_m)
        else:
            # For other operators (e.g., arithmetic), conservatively assume each
            # output may depend on every input of the combined model.
            n_out = getattr(model, "n_outputs", None)
            n_in = getattr(model, "n_inputs", None)
            if n_out is None or n_in is None:
                # Fallback via submodels' shapes if available
                n_out = left_m.shape[0] + right_m.shape[0]
                n_in = left_m.shape[1] + right_m.shape[1]
            return _all_true_matrix(int(n_out), int(n_in))

    # Leaf model: conservative default (all True)
    n_out = getattr(model, "n_outputs", None)
    n_in = getattr(model, "n_inputs", None)
    if n_out is None or n_in is None:
        # Best-effort fallback; most astropy models define these properties.
        try:
            n_in = len(getattr(model, "inputs"))
        except Exception:
            n_in = 1
        try:
            n_out = len(getattr(model, "outputs"))
        except Exception:
            n_out = 1
    return _all_true_matrix(int(n_out), int(n_in))