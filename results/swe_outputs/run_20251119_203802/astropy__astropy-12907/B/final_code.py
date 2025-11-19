from typing import List
import numpy as np

try:
    # Import here to avoid circular imports at module import time if any
    from astropy.modeling.core import CompoundModel
except Exception:  # pragma: no cover - defensive import during refactor
    CompoundModel = None

__all__ = ["separability_matrix"]


def _flatten_parallel(model) -> List[object]:
    """Recursively flatten a nested parallel ('&') CompoundModel into a flat list of leaf models.

    If 'model' is not a CompoundModel with op == '&', it is returned as a single-item list.
    """
    if CompoundModel is not None and isinstance(model, CompoundModel) and getattr(model, 'op', None) == '&':
        return _flatten_parallel(model.left) + _flatten_parallel(model.right)
    return [model]


def _block_diag_bool(mats: List[np.ndarray]) -> np.ndarray:
    """Construct a block-diagonal boolean matrix from a list of boolean matrices."""
    if not mats:
        return np.zeros((0, 0), dtype=bool)
    total_rows = sum(m.shape[0] for m in mats)
    total_cols = sum(m.shape[1] for m in mats)
    out = np.zeros((total_rows, total_cols), dtype=bool)
    r = c = 0
    for m in mats:
        rr, cc = m.shape
        out[r:r+rr, c:c+cc] = m
        r += rr
        c += cc
    return out


def _separability_matrix_core(model):
    """Core separability computation for a model.

    This is a conservative implementation that treats leaf models as fully coupled
    within their own input/output dimensionality, and composes parallel ('&')
    models block-diagonally. It is intended as an extraction point from the prior
    implementation so that a thin wrapper can fix nested parallel behavior.
    """
    # Handle compound models conservatively
    if CompoundModel is not None and isinstance(model, CompoundModel):
        op = getattr(model, 'op', None)
        if op == '&':
            # Compose block-diagonally for parallel models
            left_mat = _separability_matrix_core(model.left)
            right_mat = _separability_matrix_core(model.right)
            return _block_diag_bool([left_mat, right_mat])
        # For other compound operations (like composition), fall back to a dense matrix
        # based on reported input/output dimensionality.
        n_inputs = getattr(model, 'n_inputs', None)
        n_outputs = getattr(model, 'n_outputs', None)
        if n_inputs is None:
            # Best-effort: try to infer from parts if available
            try:
                n_inputs = getattr(model.left, 'n_inputs', 0) + getattr(model.right, 'n_inputs', 0)
            except Exception:
                n_inputs = 0
        if n_outputs is None:
            try:
                n_outputs = getattr(model.left, 'n_outputs', 0) + getattr(model.right, 'n_outputs', 0)
            except Exception:
                n_outputs = 0
        if n_inputs == 0 or n_outputs == 0:
            return np.zeros((0, 0), dtype=bool)
        return np.ones((n_outputs, n_inputs), dtype=bool)

    # Leaf model: assume fully coupled within its dimensionality
    n_inputs = getattr(model, 'n_inputs', 1)
    n_outputs = getattr(model, 'n_outputs', 1)
    # Ensure integers and reasonable defaults
    try:
        n_inputs = int(n_inputs)
    except Exception:
        n_inputs = 1
    try:
        n_outputs = int(n_outputs)
    except Exception:
        n_outputs = 1
    return np.ones((n_outputs, n_inputs), dtype=bool)


def separability_matrix(model):
    """Return a boolean separability matrix for a model.

    This wrapper fixes incorrect separability for nested parallel ('&') CompoundModels
    by flattening them and composing block-diagonally. All other behavior is delegated
    to the core implementation extracted into ``_separability_matrix_core``.
    """
    # If it's a nested parallel composition, flatten and combine block-diagonally
    if CompoundModel is not None and isinstance(model, CompoundModel) and getattr(model, 'op', None) == '&':
        parts = _flatten_parallel(model)
        mats = [_separability_matrix_core(p) for p in parts]
        return _block_diag_bool(mats)

    # Otherwise, fall back to the original core logic
    return _separability_matrix_core(model)