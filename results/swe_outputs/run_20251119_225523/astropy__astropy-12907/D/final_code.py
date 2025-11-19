import numpy as np

__all__ = ["separability_matrix"]

def separability_matrix(model):
    """
    Compute the separability matrix for a (possibly nested) Model/CompoundModel.

    This implementation correctly handles nested CompoundModels by:
    - Using block-diagonal composition for parallel combination ('&').
    - Using boolean dependency composition for serial composition ('|').
    For leaf models, if they are separable and have matching input/output arity,
    the matrix is an identity; otherwise we conservatively assume full coupling.

    Parameters
    ----------
    model : object
        An astropy Model instance or CompoundModel (possibly nested).

    Returns
    -------
    numpy.ndarray
        A boolean array of shape (n_outputs, n_inputs) where entry [i, j] is True
        if output i may depend on input j.
    """

    def _matrix(node):
        # Unwrap common wrapper attributes seen in expression trees
        # (e.g., nodes that hold a model under 'leaf', 'value', or 'model').
        if not hasattr(node, 'op') and not hasattr(node, '_tree'):
            for attr in ('leaf', 'value', 'model'):
                inner = getattr(node, attr, None)
                if inner is not None and inner is not node:
                    return _matrix(inner)

        # If this is a binary operator node (Compound), process via its op
        op = getattr(node, 'op', None)
        if op is not None and hasattr(node, 'left') and hasattr(node, 'right'):
            left = _matrix(getattr(node, 'left'))
            right = _matrix(getattr(node, 'right'))

            # Normalize op to a simple symbol
            sym = op if isinstance(op, str) else getattr(op, 'value', getattr(op, 'symbol', None))

            if sym == '&':
                # Parallel combination: block-diagonal matrix
                out = np.zeros((left.shape[0] + right.shape[0], left.shape[1] + right.shape[1]), dtype=bool)
                out[:left.shape[0], :left.shape[1]] = left
                out[left.shape[0]:, left.shape[1]:] = right
                return out

            if sym == '|':
                # Serial composition: boolean dependency composition
                # right(left(x)) => M = right @ left (boolean matmul)
                try:
                    return (right.astype(int) @ left.astype(int) > 0)
                except Exception:
                    # Fallback if shapes are inconsistent for some reason
                    return np.ones((right.shape[0], left.shape[1]), dtype=bool)

            # Unknown operator: conservatively assume full coupling of combined dims
            nout = left.shape[0] + right.shape[0]
            nin = left.shape[1] + right.shape[1]
            return np.ones((nout, nin), dtype=bool)

        # If this is a CompoundModel-like object with an internal tree, recurse into it
        tree = getattr(node, '_tree', None)
        if tree is not None:
            return _matrix(tree)

        # Treat as a leaf model
        n_in = getattr(node, 'n_inputs', len(getattr(node, 'inputs', ()) or ()))
        n_out = getattr(node, 'n_outputs', len(getattr(node, 'outputs', ()) or ()))

        # If the model defines a custom separability matrix, prefer it (avoid recursion into this function)
        meth = getattr(node, 'separability_matrix', None)
        if callable(meth):
            try:
                # If it's a bound method not pointing back to this function, use it
                func_obj = getattr(meth, '__func__', None)
                if func_obj is not separability_matrix:
                    mat = meth()
                    if isinstance(mat, np.ndarray) and mat.dtype == bool:
                        return mat
            except Exception:
                # Ignore and fall back to heuristics
                pass

        sep = getattr(node, 'separable', None)
        if sep is True and n_in == n_out:
            return np.eye(n_out, n_in, dtype=bool)

        # Default conservative assumption: each output may depend on any input
        return np.ones((n_out, n_in), dtype=bool)

    return _matrix(model)