from __future__ import annotations

import numpy as np

__all__ = ["separability_matrix"]


def separability_matrix(model):
    """
    Compute a boolean separability matrix of shape (n_outputs, n_inputs).

    Entry [i, j] is True if output i depends on input j.
    This implementation evaluates the model numerically and is robust to
    nested CompoundModels (including parallel '&' compositions) and other
    arbitrary nesting, by probing outputs while varying one input at a time.

    Parameters
    ----------
    model : astropy.modeling.Model
        The model whose input-output dependencies are being analyzed.

    Returns
    -------
    numpy.ndarray
        A boolean array of shape (n_outputs, n_inputs) where element [i, j]
        indicates whether output i depends on input j.
    """
    n_in = getattr(model, "n_inputs")
    n_out = getattr(model, "n_outputs")

    # Prepare baseline scalar arguments for evaluation.
    # Using floats tends to work for most models; if a model requires units,
    # this function assumes it can accept unitless inputs as well (as is the
    # case for many core models like pixel <-> sky transforms).
    base = [0.0] * n_in

    def _eval_out(args):
        y = model(*args)
        # Normalize to a tuple of numpy arrays for consistent comparison
        if n_out == 1:
            return (np.asarray(y),)
        return tuple(np.asarray(yi) for yi in y)

    # Use two distinct values unlikely to cancel out under typical transforms
    # to probe dependency. These are arbitrary but chosen to avoid symmetry
    # around zero for odd/even functions.
    val_a = -0.731
    val_b = 1.289

    # Baseline outputs (for constant-output detection)
    y_base = _eval_out(base)

    mat = np.zeros((n_out, n_in), dtype=bool)

    for j in range(n_in):
        args_a = list(base)
        args_b = list(base)
        args_a[j] = val_a
        args_b[j] = val_b

        y_a = _eval_out(args_a)
        y_b = _eval_out(args_b)

        for i in range(n_out):
            # An output depends on input j if changing only that input
            # changes the output value. We use allclose to account for
            # numerical noise and broadcasting behaviour.
            dep = not np.allclose(y_a[i], y_b[i], equal_nan=True)
            # As a fallback for flat regions or piecewise behaviour, also
            # consider deviation from the baseline evaluation.
            if not dep:
                dep = (not np.allclose(y_a[i], y_base[i], equal_nan=True)) or (
                    not np.allclose(y_b[i], y_base[i], equal_nan=True)
                )
            mat[i, j] = dep

    return mat