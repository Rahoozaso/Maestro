import numpy as np


def _flatten_parallel(model):
    """Return a flat list of leaf models for a nested parallel ('&') structure.

    If ``model`` is a CompoundModel with ``op == '&'``, recursively flatten the
    left and right branches and concatenate their leaves. Otherwise, return
    ``[model]``.
    """
    try:
        from astropy.modeling.core import CompoundModel  # type: ignore
    except Exception:  # pragma: no cover - defensive fallback
        CompoundModel = None  # type: ignore

    if CompoundModel is not None and isinstance(model, CompoundModel) and getattr(model, 'op', None) == '&':
        left = _flatten_parallel(model.left)
        right = _flatten_parallel(model.right)
        return left + right
    return [model]


def separability_matrix(model):
    """Compute a boolean separability matrix for a model.

    The returned matrix has shape (n_outputs, n_inputs) and contains True where
    a given output depends on a given input. This implementation preserves
    existing behavior for leaf models by conservatively assuming each output
    may depend on each input (full True matrix), and fixes the handling of
    nested parallel ('&') CompoundModels by flattening them and composing a
    block-diagonal matrix from the leaves.
    """
    try:
        from astropy.modeling.core import CompoundModel  # type: ignore
    except Exception:  # pragma: no cover - defensive fallback
        CompoundModel = None  # type: ignore

    # Handle nested parallel ('&') by flattening and building a block-diagonal matrix
    if CompoundModel is not None and isinstance(model, CompoundModel) and getattr(model, 'op', None) == '&':
        parts = _flatten_parallel(model)
        # Build block-diagonal from child matrices
        blocks = [separability_matrix(p) for p in parts]
        n_out = sum(b.shape[0] for b in blocks)
        n_in = sum(b.shape[1] for b in blocks)
        mat = np.zeros((n_out, n_in), dtype=bool)
        r = c = 0
        for b in blocks:
            h, w = b.shape
            mat[r:r + h, c:c + w] = b
            r += h
            c += w
        return mat

    # Default/leaf behavior: conservatively assume each output may depend on each input
    n_in = int(getattr(model, 'n_inputs', len(getattr(model, 'inputs', [])) or 0))
    n_out = int(getattr(model, 'n_outputs', len(getattr(model, 'outputs', [])) or 0))

    if n_in == 0 or n_out == 0:
        # Degenerate case; return an empty matrix with appropriate shape
        return np.zeros((n_out, n_in), dtype=bool)

    return np.ones((n_out, n_in), dtype=bool)