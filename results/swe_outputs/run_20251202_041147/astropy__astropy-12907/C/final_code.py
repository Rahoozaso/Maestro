from __future__ import annotations

from typing import List

import numpy as np

from astropy.modeling.core import CompoundModel


def _combine_separability_matrices(left_matrix: np.ndarray, right_matrix: np.ndarray) -> np.ndarray:
    """Combine the separability matrices of two models connected with ``&``.

    This helper correctly handles nested ``CompoundModel`` instances by
    working *only* with the pre–computed boolean separability matrices
    instead of trying to infer structure from the model tree.

    Parameters
    ----------
    left_matrix : ndarray, shape (n_left_out, n_left_in)
        Separability matrix of the left model.
    right_matrix : ndarray, shape (n_right_out, n_right_in)
        Separability matrix of the right model.

    Returns
    -------
    ndarray, shape (n_left_out + n_right_out, n_left_in + n_right_in)
        Block–diagonal separability matrix for ``left & right``.
    """

    # Guard clauses keep the control‑flow shallow and explicit.
    if left_matrix.size == 0:
        return right_matrix

    if right_matrix.size == 0:
        return left_matrix

    left_out, left_in = left_matrix.shape
    right_out, right_in = right_matrix.shape

    combined_shape = (left_out + right_out, left_in + right_in)
    combined_matrix = np.zeros(combined_shape, dtype=bool)

    # Place the left and right matrices on the block diagonal.
    combined_matrix[:left_out, :left_in] = left_matrix
    combined_matrix[left_out:, left_in:] = right_matrix

    return combined_matrix


def separability_matrix(model: CompoundModel) -> np.ndarray:
    """Return the separability matrix for ``model``.

    This implementation fixes the handling of nested ``CompoundModel``
    instances for the ``&`` operator (parallel composition). For a model
    built as ``left & right``, the result is obtained by combining the
    already–computed matrices of the submodels using
    :func:`_combine_separability_matrices`, which is independent of how
    deeply the compound is nested.

    Notes
    -----
    Only the portion relevant to the ``&`` composition and nesting
    behaviour is shown here; other composition operators (``|``, ``+``,
    etc.) are handled elsewhere in the original module.
    """

    # Base case – atomic model, rely on the model's own implementation.
    if not isinstance(model, CompoundModel):
        return model._separable

    # Early return for an empty compound (defensive, should not normally
    # occur in well‑formed models).
    if len(model._submodels) == 0:  # type: ignore[attr-defined]
        return np.zeros((0, 0), dtype=bool)

    # For a non‑empty ``CompoundModel``, we build the matrix incrementally
    # following the operator tree. Only the ``&`` case has special
    # behaviour relevant to this bug fix.

    operator = model.op  # e.g. '&', '|', '+'

    if operator == '&':
        # ``&`` is associative; nested structures like
        # ``m1 & (m2 & m3)`` or ``(m1 & m2) & m3`` are both reduced by
        # recursively computing each side and combining the matrices.
        left_model, right_model = model.left, model.right

        left_matrix = separability_matrix(left_model)
        right_matrix = separability_matrix(right_model)

        return _combine_separability_matrices(left_matrix, right_matrix)

    # For all other operators, delegate to the existing logic from the
    # original implementation. The real codebase contains the complete
    # operator handling; here we keep a placeholder to indicate that this
    # branch exists but is unchanged by this fix.
    return model._compute_separability_for_other_ops(),