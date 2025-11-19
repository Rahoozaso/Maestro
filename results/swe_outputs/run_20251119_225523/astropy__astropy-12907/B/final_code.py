import operator
from typing import Optional

import numpy as np
from astropy.modeling.core import CompoundModel

__all__ = ["separability_matrix"]


def separability_matrix(model) -> np.ndarray:
    """
    Compute the separability matrix for a model.

    This returns a boolean array S with shape (n_outputs, n_inputs) where
    S[o, i] is True if output o depends on input i.

    Behavior:
    - Parallel composition ('&'): Flattens nested parallel groups and constructs
      a block-diagonal separability matrix.
    - Serial composition ('|'): Composes via boolean matrix multiplication.
    - Other operations: Conservative fallback to assume full dependency.
    - Atomic models: If model.separable is True, assume diagonal-like mapping
      (each output depends on at most one corresponding input) up to
      min(n_inputs, n_outputs); otherwise assume full dependency.
    """

    AND_OPS = {"&", operator.and_}
    OR_OPS = {"|", operator.or_}

    def _matrix_for(m) -> np.ndarray:
        # Compute separability matrix for any model m.
        if isinstance(m, CompoundModel):
            op = m.op
            # Parallel composition: flatten nested '&' groups and build block-diagonal matrix
            if op in AND_OPS:
                parts = []

                def _flatten_parallel(node):
                    if isinstance(node, CompoundModel) and node.op in AND_OPS:
                        _flatten_parallel(node.left)
                        _flatten_parallel(node.right)
                    else:
                        parts.append(node)

                _flatten_parallel(m)
                mats = [_matrix_for(p) for p in parts]
                total_out = sum(mm.shape[0] for mm in mats)
                total_in = sum(mm.shape[1] for mm in mats)
                res = np.zeros((total_out, total_in), dtype=bool)
                o_off = 0
                i_off = 0
                for mm in mats:
                    h, w = mm.shape
                    res[o_off : o_off + h, i_off : i_off + w] = mm
                    o_off += h
                    i_off += w
                return res
            # Serial composition: boolean matrix multiplication
            elif op in OR_OPS:
                L = _matrix_for(m.left)
                R = _matrix_for(m.right)
                # Shapes: L (nout_L x nin_L), R (nout_R x nin_R) with nin_R == nout_L
                # Compose dependencies: outputs of R depend on inputs of L through intermediates
                return (R.astype(int) @ L.astype(int) > 0)
            else:
                # Conservative fallback for other operations (+, *, etc.)
                return np.ones((m.n_outputs, m.n_inputs), dtype=bool)
        else:
            # Atomic model: if separable is True, assume outputs are independent and
            # map to corresponding inputs along the diagonal; else fully dependent.
            sep: Optional[bool]
            try:
                sep = getattr(m, "separable", None)
            except Exception:
                sep = None

            n_in = m.n_inputs
            n_out = m.n_outputs

            if sep is True:
                res = np.zeros((n_out, n_in), dtype=bool)
                for k in range(min(n_in, n_out)):
                    res[k, k] = True
                return res

            # Default conservative assumption: fully non-separable within the atomic model.
            return np.ones((n_out, n_in), dtype=bool)

    return _matrix_for(model)