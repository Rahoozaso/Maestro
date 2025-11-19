import numpy as np
from astropy.modeling.core import CompoundModel
from typing import Any

__all__ = ["separability_matrix"]


def _boolean_matmul(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Compute boolean matrix product for composition of models.

    A: shape (m x k), B: shape (k x n) -> returns (m x n) boolean array
    where (A @ B) > 0 using integer multiplication then thresholding.
    """
    return (A.astype(np.uint8) @ B.astype(np.uint8)) > 0


def _separability_matrix_recursive(model: Any) -> np.ndarray:
    """
    Return a boolean matrix M of shape (model.n_outputs, model.n_inputs)
    where M[i, j] indicates whether output i depends on input j. Handles
    nested CompoundModels by recursion.
    """
    # Base case: non-compound models
    if not isinstance(model, CompoundModel):
        ni = getattr(model, 'n_inputs', 1)
        no = getattr(model, 'n_outputs', 1)

        # If the model provides its own separability information, use it
        # This allows specialized models to override the conservative default
        provided = getattr(model, 'separability_matrix', None)
        if provided is not None and not callable(provided):
            return np.array(provided, dtype=bool, copy=False)

        # Default assumptions:
        # - 1D -> 1D models: trivially separable
        # - Otherwise, conservatively assume each output may depend on each input
        if ni == 1 and no == 1:
            return np.array([[True]], dtype=bool)
        return np.ones((no, ni), dtype=bool)

    # CompoundModel: combine left/right by operator
    left = model.left
    right = model.right
    op = model.op  # expected '&' for parallel, '|' for composition

    Ml = _separability_matrix_recursive(left)
    Mr = _separability_matrix_recursive(right)

    if op == '&':
        # Parallel: block-diagonal assembly
        no = Ml.shape[0] + Mr.shape[0]
        ni = Ml.shape[1] + Mr.shape[1]
        M = np.zeros((no, ni), dtype=bool)
        M[:Ml.shape[0], :Ml.shape[1]] = Ml
        M[Ml.shape[0]:, Ml.shape[1]:] = Mr
        return M
    elif op == '|':
        # Composition: boolean matrix multiplication (right after left)
        # For y = right(left(x)), dependencies are M = Mr @ Ml in boolean algebra
        return _boolean_matmul(Mr, Ml)
    else:
        # Fallback for other operators: conservative assumption
        ni = left.n_inputs + right.n_inputs
        no = left.n_outputs + right.n_outputs
        return np.ones((no, ni), dtype=bool)


def separability_matrix(model: Any) -> np.ndarray:
    """
    Compute the separability matrix of a model, correctly handling nested CompoundModels.

    Returns
    -------
    numpy.ndarray (dtype=bool)
        Matrix M with shape (model.n_outputs, model.n_inputs) where M[i, j] is True
        iff output i depends (directly or indirectly) on input j.
    """
    M = _separability_matrix_recursive(model)
    # Normalize to a numpy boolean array
    return np.array(M, dtype=bool, copy=False)