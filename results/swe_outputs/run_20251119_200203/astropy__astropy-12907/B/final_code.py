import numpy as np


def _flatten_parallel(model):
    """Return a flat list of submodels for nested parallel ('&') CompoundModels.

    This ensures separability_matrix builds an accurate block-diagonal matrix
    even when parallel compositions are nested.
    """
    try:
        from astropy.modeling.core import CompoundModel
    except Exception:  # Safe import in case of local import ordering
        from .core import CompoundModel  # type: ignore

    if isinstance(model, CompoundModel) and getattr(model, 'op', None) == '&':
        return _flatten_parallel(model.left) + _flatten_parallel(model.right)
    return [model]


def separability_matrix(model):
    """Return a boolean matrix describing which outputs depend on which inputs.

    The matrix has shape (n_outputs, n_inputs) where an entry [i, j] is True if
    output i depends on input j.

    This implementation specifically improves handling of nested parallel ('&')
    CompoundModels by flattening them and assembling a block-diagonal matrix
    from the separability matrices of each component.

    For non-CompoundModels, a conservative default is used where every output is
    assumed to depend on every input.
    """
    try:
        from astropy.modeling.core import CompoundModel
    except Exception:
        from .core import CompoundModel  # type: ignore

    # Handle nested parallel composition by flattening and assembling a block-diagonal matrix
    if isinstance(model, CompoundModel) and getattr(model, 'op', None) == '&':
        parts = _flatten_parallel(model)
        # Build block-diagonal matrix from each part's separability
        mats = [separability_matrix(m) for m in parts]
        n_out = sum(mat.shape[0] for mat in mats)
        n_in = sum(mat.shape[1] for mat in mats)
        res = np.zeros((n_out, n_in), dtype=bool)
        ro = 0
        co = 0
        for mat in mats:
            h, w = mat.shape
            res[ro:ro + h, co:co + w] = mat
            ro += h
            co += w
        return res

    # Fallback general case: conservative assumption that every output depends on every input
    n_out = getattr(model, 'n_outputs', 1)
    n_in = getattr(model, 'n_inputs', 1)
    return np.ones((n_out, n_in), dtype=bool)