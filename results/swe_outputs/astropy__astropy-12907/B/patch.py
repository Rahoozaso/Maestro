import numpy as np
from typing import List

__all__ = [
    "separability_matrix",
    "_flatten_join",
]


def _flatten_join(model):
    """Return a flat list of leaf models for a nested join ('&') CompoundModel.

    This preserves the left-to-right order of the join tree and avoids losing
    internal separability information when computing the block-diagonal structure.
    """
    try:
        # Imported here to avoid import cycles at module import-time
        from astropy.modeling.core import CompoundModel  # type: ignore
    except Exception:  # pragma: no cover - safety in case of local import issues
        CompoundModel = None  # type: ignore

    parts: List[object] = []

    def _recurse(m):
        if CompoundModel is not None and isinstance(m, CompoundModel) and getattr(m, 'op', None) == '&':
            # Assuming public attributes 'left' and 'right' for CompoundModel
            _recurse(getattr(m, 'left'))
            _recurse(getattr(m, 'right'))
        else:
            parts.append(m)

    _recurse(model)
    return parts


def separability_matrix(model):
    """Compute the separability matrix for a model.

    The matrix is a boolean array of shape (n_inputs, n_outputs) where entry
    (i, j) is True if output j depends on input i. For parallel ("&") compound
    models, nested joins are flattened and a block-diagonal matrix is assembled
    from child submatrices to correctly represent separability across inputs and
    outputs of joined submodels.
    """
    # Local import to avoid potential import-time cycles
    try:
        from astropy.modeling.core import CompoundModel  # type: ignore
    except Exception:  # pragma: no cover - safety
        CompoundModel = None  # type: ignore

    # Handle nested joins ('&') by flattening and assembling block-diagonal
    if CompoundModel is not None and isinstance(model, CompoundModel) and getattr(model, 'op', None) == '&':
        parts = _flatten_join(model)
        # Recursively compute submatrices for each leaf
        submats = [separability_matrix(p) for p in parts]
        if not submats:
            return np.zeros((0, 0), dtype=bool)

        # Block-diagonal assembly
        n_in = sum(sm.shape[0] for sm in submats)
        n_out = sum(sm.shape[1] for sm in submats)
        result = np.zeros((n_in, n_out), dtype=bool)

        i0 = 0
        o0 = 0
        for sm in submats:
            i, o = sm.shape
            result[i0:i0 + i, o0:o0 + o] = sm
            i0 += i
            o0 += o

        return result

    # Fallback: for non-join models, conservatively assume each output depends
    # on all inputs unless more specific logic is available in upstream code.
    n_in = getattr(model, 'n_inputs', None)
    if n_in is None:
        inputs = getattr(model, 'inputs', None)
        if inputs is not None:
            n_in = len(inputs)
        else:
            n_in = 1

    n_out = getattr(model, 'n_outputs', None)
    if n_out is None:
        outputs = getattr(model, 'outputs', None)
        if outputs is not None:
            n_out = len(outputs)
        else:
            n_out = 1

    return np.ones((n_in, n_out), dtype=bool)