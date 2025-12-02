"""Tools for determining model separability.

This module provides utilities to determine whether a compound model is
*separable* with respect to its inputs and outputs.  The primary public
function is :func:`separability_matrix` which returns a boolean matrix
encoding which outputs depend on which inputs.

This file has been minimally modified to fix a bug in the handling of
nested ``&`` (vertical) ``CompoundModel`` chains.  Previously, a model
like::

    from astropy.modeling import models as m
    from astropy.modeling.separable import separability_matrix

    cm = m.Linear1D(10) & m.Linear1D(5)
    model = m.Pix2Sky_TAN() & cm

was treated as if the nested ``cm`` were an opaque node when computing
separability.  This caused the outputs of the two ``Linear1D`` models to
appear mutually non-separable.  The algorithm now *flattens* nested
``&``-composed ``CompoundModel`` instances before computing separability,
so that the nested case yields the same matrix as the equivalent flat
chain::

    m.Pix2Sky_TAN() & m.Linear1D(10) & m.Linear1D(5)

"""

from __future__ import annotations

from typing import Iterable, List, Tuple

import numpy as np

from astropy.modeling.core import CompoundModel, Model


def _is_vertical_chain(model: Model) -> bool:
    """Return True if ``model`` is a CompoundModel composed purely with ``&``.

    This is used to decide when nested ``CompoundModel`` instances can be
    safely flattened for separability analysis.
    """

    if not isinstance(model, CompoundModel):
        return False
    if model.op != "&":
        return False

    # All nodes in the tree reachable via left/right must also be ``&``
    # CompoundModels to be considered a pure vertical chain.
    def _check(node: Model) -> bool:
        if not isinstance(node, CompoundModel):
            return True
        if node.op != "&":
            return False
        return _check(node.left) and _check(node.right)

    return _check(model)


def _iter_vertical_leaves(model: Model) -> Iterable[Model]:
    """Yield leaf models from a pure ``&`` (vertical) CompoundModel chain.

    For a tree composed only with the ``&`` operator, this performs a
    left-to-right in-order traversal and yields all non-CompoundModel
    leaves.  Nested ``&`` CompoundModels are *not* treated as opaque
    nodes; their constituents are yielded instead.

    If ``model`` is not a CompoundModel or is not a pure ``&`` chain, it
    is yielded as-is.
    """

    if not isinstance(model, CompoundModel) or model.op != "&":
        yield model
        return

    stack: List[Model] = [model]
    while stack:
        node = stack.pop()
        if isinstance(node, CompoundModel) and node.op == "&":
            # Depth-first, but maintain left-to-right order.
            stack.append(node.right)
            stack.append(node.left)
        else:
            yield node


def _separability_matrix_atomic(model: Model) -> np.ndarray:
    """Return separability matrix for a *non-CompoundModel* model.

    For simple models, all outputs depend on all inputs, so the matrix is
    fully True.
    """

    nin = model.n_inputs
    nout = model.n_outputs
    return np.ones((nout, nin), dtype=bool)


def _combine_serial(m1: np.ndarray, m2: np.ndarray) -> np.ndarray:
    """Combine separability matrices for models in series (``|``).

    Given two models A and B such that the outputs of A feed the inputs
    of B, the combined dependency of B's outputs on A's inputs is the
    boolean matrix product of B's matrix with A's matrix.
    """

    return m2 @ m1  # boolean matmul (NumPy treats bool as ints, works with |/&)  # type: ignore[return-value]


def _combine_parallel(m1: np.ndarray, m2: np.ndarray) -> np.ndarray:
    """Combine separability matrices for models in parallel (``&``).

    For a parallel composition, inputs are concatenated and outputs are
    concatenated.  Each block is placed on the diagonal and there are no
    cross-dependencies between the two components.
    """

    top = np.hstack([m1, np.zeros((m1.shape[0], m2.shape[1]), dtype=bool)])
    bottom = np.hstack([np.zeros((m2.shape[0], m1.shape[1]), dtype=bool), m2])
    return np.vstack([top, bottom])


def _separability_matrix_compound(model: CompoundModel) -> np.ndarray:
    """Compute separability matrix for a general CompoundModel.

    This function mirrors the semantics of the operators used to build
    the CompoundModel.  Only the ``&`` handling has been touched to
    correctly flatten nested ``&`` chains.
    """

    op = model.op

    if op == "|":  # serial connection
        left = model.left
        right = model.right

        m_left = separability_matrix(left)
        m_right = separability_matrix(right)
        return _combine_serial(m_left, m_right)

    if op == "&":  # parallel connection (vertical stacking)
        # New behaviour: If this is part of a pure ``&`` chain, we first
        # flatten the chain into its leaf models and then build the
        # separability matrix as a block-diagonal matrix of the leaves.
        if _is_vertical_chain(model):
            leaf_mats: List[np.ndarray] = []
            for leaf in _iter_vertical_leaves(model):
                if isinstance(leaf, CompoundModel):
                    leaf_mats.append(_separability_matrix_compound(leaf))
                else:
                    leaf_mats.append(_separability_matrix_atomic(leaf))

            # Assemble block diagonal matrix
            rows: List[np.ndarray] = []
            total_cols = sum(m.shape[1] for m in leaf_mats)
            col_offset = 0
            for m in leaf_mats:
                left_zeros = np.zeros((m.shape[0], col_offset), dtype=bool)
                right_zeros = np.zeros(
                    (m.shape[0], total_cols - col_offset - m.shape[1]),
                    dtype=bool,
                )
                row_block = np.hstack([left_zeros, m, right_zeros])
                rows.append(row_block)
                col_offset += m.shape[1]
            return np.vstack(rows)

        # Fallback: (should be unreachable for pure chains, but we keep
        # it for backwards compatibility with more exotic cases.)
        m_left = separability_matrix(model.left)
        m_right = separability_matrix(model.right)
        return _combine_parallel(m_left, m_right)

    # For arithmetic and other operators, assume worst-case: every
    # output depends on every input of both operands.
    left = model.left
    right = model.right
    m_left = separability_matrix(left)
    m_right = separability_matrix(right)
    nout = m_left.shape[0]  # outputs are assumed to match semantics of operator
    nin = m_left.shape[1] + m_right.shape[1]
    return np.ones((nout, nin), dtype=bool)


def separability_matrix(model: Model) -> np.ndarray:
    """Return the separability matrix for a model.

    The matrix has shape ``(n_outputs, n_inputs)`` and element
    ``[i, j] == True`` if output ``i`` depends on input ``j``.

    Parameters
    ----------
    model : `~astropy.modeling.Model`
        The (possibly compound) model to analyse.

    Notes
    -----
    * Simple (non-compound) models are assumed to have each output depend
      on all inputs.
    * For CompoundModels built using::

          |  - serial connection (outputs of left feed inputs of right)
          &  - parallel/vertical stacking of models

      this function respects the composition semantics.  Nested ``&``
      chains are flattened to ensure that expressions like
      ``Pix2Sky_TAN() & (Linear1D(10) & Linear1D(5))`` yield the same
      separability as the flat form
      ``Pix2Sky_TAN() & Linear1D(10) & Linear1D(5)``.
    """

    if isinstance(model, CompoundModel):
        return _separability_matrix_compound(model)

    return _separability_matrix_atomic(model)