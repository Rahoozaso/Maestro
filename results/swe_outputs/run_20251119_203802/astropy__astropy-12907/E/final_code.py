import numpy as np
from typing import List

__all__ = ["separability_matrix"]


def separability_matrix(model):
    """
    Compute the separability (dependency) matrix for a model, returning a
    boolean array of shape (n_outputs, n_inputs) where entry (i, j) is True
    if output i depends on input j.

    This implementation explicitly flattens nested parallel ('&') compositions
    and uses boolean algebra for series ('|') composition to ensure associativity
    and correct behavior for nested CompoundModels.

    Notes
    -----
    - Parallel composition ('&'): The overall matrix is a block-diagonal of the
      child dependency matrices. Nested parallel structures are flattened to
      construct the correct block-diagonal.
    - Series composition ('|'): The overall matrix is the boolean matrix
      multiplication (OR-over-AND) of the right matrix by the left matrix, i.e.,
      C = B o A, where A is the left dependency matrix and B is the right.
    - Addition ('+'): The overall matrix is the element-wise OR of the two
      matrices (with conservative padding if shapes do not match).
    - Base models: For leaf models, if the number of inputs and outputs are
      available, a conservative dependency matrix of ones is returned (each
      output may depend on each input). This ensures correctness, though it may
      be conservative for certain mapping-like models.
    """

    def _op(m):
        return getattr(m, "op", None)

    def _is_parallel(m):
        return _op(m) == "&"

    def _is_series(m):
        return _op(m) == "|"

    def _is_sum(m):
        return _op(m) == "+"

    def _flatten_parallel(m):
        parts: List[object] = []
        stack: List[object] = [m]
        while stack:
            cur = stack.pop()
            if _is_parallel(cur):
                # CompoundModel with parallel composition
                stack.append(getattr(cur, "right"))
                stack.append(getattr(cur, "left"))
            else:
                parts.append(cur)
        parts.reverse()
        return parts

    def _block_diag_bool(mats):
        total_o = sum(mat.shape[0] for mat in mats)
        total_i = sum(mat.shape[1] for mat in mats)
        out = np.zeros((total_o, total_i), dtype=bool)
        o_off = 0
        i_off = 0
        for mat in mats:
            r, c = mat.shape
            out[o_off:o_off + r, i_off:i_off + c] = mat
            o_off += r
            i_off += c
        return out

    def _bool_matmul(B, A):
        """
        Boolean matrix multiplication (OR over AND): C = B o A
        Shapes: A (k, n_inputs), B (m_outputs, k) -> C (m_outputs, n_inputs)
        """
        return (B.astype(np.uint8) @ A.astype(np.uint8)) > 0

    def _mat(m):
        # Parallel composition: block-diagonal of child matrices, with flattening
        if _is_parallel(m):
            parts = _flatten_parallel(m)
            mats = [_mat(p) for p in parts]
            return _block_diag_bool(mats)

        # Series composition: boolean matrix multiplication
        if _is_series(m):
            left = getattr(m, "left")
            right = getattr(m, "right")
            A = _mat(left)   # maps left outputs -> left inputs (oL x iL)
            B = _mat(right)  # maps right outputs -> right inputs (oR x iR), with iR == oL
            return _bool_matmul(B, A)

        # Addition/summing composition: element-wise OR of dependencies
        if _is_sum(m):
            left = getattr(m, "left")
            right = getattr(m, "right")
            A = _mat(left)
            B = _mat(right)
            if A.shape == B.shape:
                return np.logical_or(A, B)
            # Conservative fallback if shapes mismatch: pad and OR
            rows = max(A.shape[0], B.shape[0])
            cols = max(A.shape[1], B.shape[1])
            A2 = np.zeros((rows, cols), dtype=bool)
            B2 = np.zeros((rows, cols), dtype=bool)
            A2[:A.shape[0], :A.shape[1]] = A
            B2[:B.shape[0], :B.shape[1]] = B
            return np.logical_or(A2, B2)

        # Base model: conservative assumption that each output may depend on each input
        n_in = getattr(m, "n_inputs", None)
        n_out = getattr(m, "n_outputs", None)
        if n_in is None or n_out is None:
            # Fallback for non-standard models; a 1x1 True conveys dependency presence
            return np.array([[True]], dtype=bool)
        return np.ones((n_out, n_in), dtype=bool)

    return _mat(model)