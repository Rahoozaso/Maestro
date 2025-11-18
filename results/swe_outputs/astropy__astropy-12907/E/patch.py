import numpy as np
from functools import reduce
from typing import Any

try:
    # Preferred relative import within astropy.modeling package
    from .core import CompoundModel
except Exception:  # pragma: no cover - fallback if layout changes
    # Fallback import path
    from astropy.modeling.core import CompoundModel  # type: ignore


def _is_parallel(model: Any) -> bool:
    """Return True if the model is a CompoundModel composed with the '&' operator."""
    return isinstance(model, CompoundModel) and getattr(model, 'op', None) == '&'


def _flatten_parallel(model: Any):
    """
    Flatten nested parallel ('&') CompoundModels to a single-level '&'-chain.

    This preserves the associativity of '&' for the separability analysis so that
    expressions like A & (B & C) behave the same as A & B & C.
    """

    if not _is_parallel(model):
        return model

    components = []

    def _collect(m):
        if _is_parallel(m):
            _collect(m.left)
            _collect(m.right)
        else:
            components.append(m)

    _collect(model)

    # Rebuild as a flat '&' chain, preserving left-to-right ordering
    return reduce(lambda a, b: a & b, components)


def _separability_matrix_impl(model: Any) -> np.ndarray:
    """
    Compute the separability matrix for a model.

    For a general (atomic) model, this conservatively assumes that each output
    depends on all inputs, yielding a full True matrix of shape
    (model.n_outputs, model.n_inputs).

    For parallel compositions using the '&' operator, the resulting separability
    matrix is block-diagonal: inputs and outputs from different parallel branches
    are independent of each other.

    For other compound operations we conservatively assume full dependency.
    """

    def _matrix_for(m) -> np.ndarray:
        # Compound parallel composition: block-diagonal combination
        if isinstance(m, CompoundModel):
            op = getattr(m, 'op', None)
            if op == '&':
                left = getattr(m, 'left')
                right = getattr(m, 'right')
                ml = _matrix_for(left)
                mr = _matrix_for(right)
                ol, il = ml.shape
                or_, ir = mr.shape
                out = np.zeros((ol + or_, il + ir), dtype=bool)
                # Upper-left block for left branch
                out[:ol, :il] = ml
                # Lower-right block for right branch
                out[ol:, il:] = mr
                return out
            else:
                # For non-parallel compound operations (e.g., serial composition, arithmetic),
                # conservatively assume all outputs depend on all inputs.
                return np.ones((m.n_outputs, m.n_inputs), dtype=bool)

        # Atomic model: assume full dependency by default
        return np.ones((m.n_outputs, m.n_inputs), dtype=bool)

    return _matrix_for(model)


def separability_matrix(model: Any) -> np.ndarray:
    """
    Compute the separability matrix of a model.

    This wrapper first normalizes nested parallel ('&') CompoundModels to a flat
    form to ensure associativity of '&' is respected, then delegates to the
    original implementation now in _separability_matrix_impl.
    """
    # Normalize nested parallel structures like A & (B & C) => A & B & C
    try:
        normalized = _flatten_parallel(model)
    except NameError:
        # If helper is not yet available for any reason, fall back to original
        normalized = model
    return _separability_matrix_impl(normalized)