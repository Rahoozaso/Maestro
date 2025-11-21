from typing import List, Tuple
import numpy as np

try:
    # Import from astropy when available
    from astropy.modeling.core import CompoundModel  # type: ignore
except Exception:  # pragma: no cover - fallback in non-astropy environments
    class CompoundModel:  # type: ignore
        pass


def _flatten_parallel(model):
    """
    Flatten nested parallel ('&') CompoundModels into a linear list of leaf
    submodels with corresponding input/output index spans relative to the
    parent model. Returns (leaves, in_spans, out_spans). Each span is a
    (start, end) half-open interval.
    """
    if not isinstance(model, CompoundModel) or getattr(model, 'op', None) != '&':
        return [model], [(0, model.n_inputs)], [(0, model.n_outputs)]

    left, right = model.left, model.right

    left_leaves, left_in_spans, left_out_spans = _flatten_parallel(left)
    right_leaves, right_in_spans, right_out_spans = _flatten_parallel(right)

    in_offset = left.n_inputs
    out_offset = left.n_outputs

    right_in_spans = [(a + in_offset, b + in_offset) for (a, b) in right_in_spans]
    right_out_spans = [(a + out_offset, b + out_offset) for (a, b) in right_out_spans]

    leaves = left_leaves + right_leaves
    in_spans = left_in_spans + right_in_spans
    out_spans = left_out_spans + right_out_spans

    return leaves, in_spans, out_spans


def separability_matrix(model):
    """
    Compute a boolean separability (dependency) matrix of shape
    (n_outputs, n_inputs) where entry (i, j) is True if output i depends on
    input j.

    This implementation specifically fixes handling for nested parallel ('&')
    CompoundModels by flattening them and assembling a block-diagonal matrix
    across the leaves. For serial composition ('|'), a conservative boolean
    composition is used. For atomic models, a conservative full-dependency
    matrix (all True) is returned.
    """
    # Handle parallel composition via flattening
    if isinstance(model, CompoundModel) and getattr(model, 'op', None) == '&':
        leaves, in_spans, out_spans = _flatten_parallel(model)
        M = np.zeros((model.n_outputs, model.n_inputs), dtype=bool)
        for leaf, (c0, c1), (r0, r1) in zip(leaves, in_spans, out_spans):
            S_leaf = separability_matrix(leaf)
            # Sanity: ensure the leaf matrix matches its I/O span
            expected_shape = (r1 - r0, c1 - c0)
            if S_leaf.shape != expected_shape:
                # Conservative fallback to preserve shape
                S_leaf = np.ones(expected_shape, dtype=bool)
            M[r0:r1, c0:c1] = S_leaf
        return M

    # Handle serial composition ('|') with boolean matrix composition
    if isinstance(model, CompoundModel) and getattr(model, 'op', None) == '|':
        left = model.left
        right = model.right
        S_left = separability_matrix(left)   # shape: (left.n_outputs, left.n_inputs)
        S_right = separability_matrix(right) # shape: (right.n_outputs, right.n_inputs)

        # For composition, right's inputs are left's outputs
        if S_right.shape[1] != S_left.shape[0]:
            # Conservative fallback if shapes do not align
            return np.ones((model.n_outputs, model.n_inputs), dtype=bool)

        # Boolean composition: (S_right ∘ S_left)[i, j] = any_k S_right[i, k] & S_left[k, j]
        M = np.any(S_right[:, :, None] & S_left[None, :, :], axis=1)
        return M

    # Atomic models or unknown composition: conservative full dependency
    try:
        n_out = model.n_outputs
        n_in = model.n_inputs
    except Exception:
        # Fallback conservative empty matrix if model does not expose sizes
        return np.array([[]], dtype=bool)

    return np.ones((n_out, n_in), dtype=bool)