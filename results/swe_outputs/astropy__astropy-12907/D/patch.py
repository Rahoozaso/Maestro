import numpy as np
from typing import List, Tuple

try:
    # Importing the public modeling classes so we can introspect compound models safely
    from astropy.modeling.core import CompoundModel, Model
except Exception:  # pragma: no cover - fallback typing only
    CompoundModel = object  # type: ignore
    Model = object  # type: ignore

__all__ = [
    "separability_matrix",
    "_flatten_parallel",
    "_block_diag_bool",
]


def _get_operator(model) -> str:
    """
    Best-effort retrieval of the operator symbol for a CompoundModel.

    Returns a string like '&' or '|' when available; otherwise an empty string.
    """
    # Common attribute names used in astropy's CompoundModel internals
    for attr in ("op", "_operator", "operator", "_op"):
        if hasattr(model, attr):
            op = getattr(model, attr)
            # Expected to be a string for composition operators
            if isinstance(op, str):
                return op
            # If callable or other, we cannot easily map - return empty
    return ""


def _get_left_right(model) -> Tuple[object, object]:
    """
    Best-effort retrieval of the left and right submodels for a CompoundModel.

    Tries multiple attribute names to be resilient to internal variations.
    """
    left = None
    right = None
    for attr in ("_left", "left", "lhs", "left_model"):
        if hasattr(model, attr):
            left = getattr(model, attr)
            break
    for attr in ("_right", "right", "rhs", "right_model"):
        if hasattr(model, attr):
            right = getattr(model, attr)
            break
    if left is None or right is None:
        raise AttributeError("Could not determine left/right submodels from CompoundModel")
    return left, right


def _flatten_parallel(model):
    """
    Return a flat list of leaf models for a possibly nested '&' composition.

    If model is a CompoundModel with the parallel operator ('&'), recursively
    flatten its left and right branches. Otherwise, return [model].
    The order preserves input ordering (left-to-right) as in '&'.
    """
    if isinstance(model, CompoundModel) and _get_operator(model) == "&":
        left, right = _get_left_right(model)
        return _flatten_parallel(left) + _flatten_parallel(right)
    # Atomic model or non-parallel compound treated as a leaf for this helper
    return [model]


def _block_diag_bool(mats: List[np.ndarray]) -> np.ndarray:
    """
    Return a boolean block-diagonal matrix from a list of boolean 2D arrays.

    This avoids a SciPy dependency and ensures off-diagonal False blocks.
    """
    if not mats:
        return np.zeros((0, 0), dtype=bool)
    total_r = sum(int(m.shape[0]) for m in mats)
    total_c = sum(int(m.shape[1]) for m in mats)
    out = np.zeros((total_r, total_c), dtype=bool)
    r = 0
    c = 0
    for m in mats:
        rr, cc = m.shape
        out[r : r + rr, c : c + cc] = m
        r += rr
        c += cc
    return out


def _atomic_separability_matrix(model: object) -> np.ndarray:
    """
    Compute a conservative separability matrix for an atomic (non-Compound) model.

    Default assumption: each output may depend on every input. This is correct
    for many models and conservative otherwise. For 1D->1D models this yields [[True]],
    and for models like Pix2Sky TAN (2->2) it yields a full 2x2 True matrix.
    """
    # We expect astropy Model API to provide n_inputs and n_outputs
    try:
        n_in = int(getattr(model, "n_inputs"))
        n_out = int(getattr(model, "n_outputs"))
    except Exception as exc:  # pragma: no cover
        raise TypeError(
            "Model object must define n_inputs and n_outputs to compute separability"
        ) from exc
    return np.ones((n_out, n_in), dtype=bool)


def separability_matrix(model) -> np.ndarray:
    """
    Compute the separability matrix for a model, correctly handling nested
    parallel ('&') CompoundModels.

    - For parallel ('&') compositions, recursively flatten nested '&' chains
      and build a boolean block-diagonal matrix from the leaf models' matrices.
    - For serial ('|') compositions, propagate dependencies via boolean
      matrix multiplication: M = B ∘ A where ∘ uses OR over AND semantics.
    - For atomic/non-compound models, assume each output can depend on every
      input (conservative default), unless overridden by upstream combination rules.

    Returns a boolean array of shape (n_outputs, n_inputs), where entry [i, j]
    indicates whether output i depends on input j.
    """
    # Parallel composition: flatten and block-diagonalize
    if isinstance(model, CompoundModel) and _get_operator(model) == "&":
        leaves = _flatten_parallel(model)
        sub_mats = [separability_matrix(m) for m in leaves]
        return _block_diag_bool(sub_mats)

    # Serial composition: boolean dependency propagation
    if isinstance(model, CompoundModel) and _get_operator(model) == "|":
        left, right = _get_left_right(model)
        # A: dependencies of left's outputs on left's inputs
        A = separability_matrix(left)
        # B: dependencies of right's outputs on right's inputs (which are left's outputs)
        B = separability_matrix(right)
        # Composition: outputs of right depend on inputs of left according to boolean matmul
        # Shapes: B (n_out_right, n_in_right == n_out_left), A (n_out_left, n_in_left)
        # Result: (n_out_right, n_in_left)
        M = (B.astype(int) @ A.astype(int)) > 0
        return M

    # Other operators: fall back to conservative assumption for this fix's scope
    # or if not a CompoundModel: treat as atomic model
    return _atomic_separability_matrix(model)