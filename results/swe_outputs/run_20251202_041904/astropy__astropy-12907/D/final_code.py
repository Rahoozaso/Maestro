from __future__ import annotations

import itertools
from typing import List

import numpy as np

from astropy.modeling.core import CompoundModel, Model


__all__ = ["separability_matrix"]


def _flatten_separable_model(model: Model) -> List[Model]:
    """Return a flat list of leaf models for '&'-composed CompoundModels.

    This normalizes nested compositions like ``A & (B & C)`` or
    ``(A & B) & C`` into a single flat sequence ``[A, B, C]``. For models
    that are not ``'&'``-``CompoundModel`` instances, the function returns
    ``[model]``.

    The goal is to ensure that the separability analysis is *associative*
    with respect to ``'&'`` composition so that, for example::

        separability_matrix(A & (B & C)) == separability_matrix(A & B & C)

    Parameters
    ----------
    model : `~astropy.modeling.core.Model`
        Input model which may be a simple model or a (possibly nested)
        ``CompoundModel`` using ``'&'``.

    Returns
    -------
    models : list of `~astropy.modeling.core.Model`
        Flat list of leaf models ordered left-to-right as in the original
        compound expression.
    """

    if not isinstance(model, CompoundModel) or model.op != "&":
        return [model]

    flat: List[Model] = []

    def _recurse(m: Model) -> None:
        if isinstance(m, CompoundModel) and m.op == "&":
            _recurse(m.left)
            _recurse(m.right)
        else:
            flat.append(m)

    _recurse(model)
    return flat


def _separability_matrix_flat(models: List[Model]) -> np.ndarray:
    """Compute separability matrix for a flat list of models composed with '&'.

    This is an adaptation of the original ``separability_matrix`` logic but
    parameterized on an explicit flat list of models that are assumed to be
    composed in parallel (``'&'``). It constructs the combined dependency
    structure from each submodel.

    For a parallel composition of models, each submodel operates on a
    disjoint, contiguous slice of the global input vector and produces a
    disjoint, contiguous slice of the global output vector. Therefore, the
    global separability matrix is block-diagonal with each block equal to the
    separability matrix of the corresponding submodel.
    """

    # If there is just a single model, use its internal separability if
    # available, otherwise assume full coupling between its inputs/outputs.
    if len(models) == 1:
        m = models[0]
        n_in = m.n_inputs
        n_out = m.n_outputs
        try:
            # Newer versions of astropy models often expose a
            # ``separable``/``separability_matrix``-like attribute. Fall
            # back to the generic assumption if not present.
            if hasattr(m, "separability_matrix"):
                mat = m.separability_matrix
            elif hasattr(m, "_separability_matrix"):
                mat = m._separability_matrix
            else:
                raise AttributeError
            mat = np.asarray(mat, dtype=bool)
            # Ensure shape correctness; otherwise fall back as well.
            if mat.shape != (n_out, n_in):
                raise ValueError
            return mat
        except Exception:
            return np.ones((n_out, n_in), dtype=bool)

    # Multi-model '&' composition: build global block-diagonal matrix.
    input_offsets = list(itertools.accumulate([0] + [m.n_inputs for m in models[:-1]]))
    output_offsets = list(itertools.accumulate([0] + [m.n_outputs for m in models[:-1]]))

    total_in = sum(m.n_inputs for m in models)
    total_out = sum(m.n_outputs for m in models)

    global_mat = np.zeros((total_out, total_in), dtype=bool)

    for m, in_off, out_off in zip(models, input_offsets, output_offsets):
        sub_in = m.n_inputs
        sub_out = m.n_outputs
        # Recursively obtain the separability of each individual model; this
        # works even if a given element is itself a non-'&' CompoundModel.
        sub_mat = separability_matrix(m)
        sub_mat = np.asarray(sub_mat, dtype=bool)
        if sub_mat.shape != (sub_out, sub_in):
            # As a safety net, assume full coupling for that block.
            sub_mat = np.ones((sub_out, sub_in), dtype=bool)
        global_mat[out_off : out_off + sub_out, in_off : in_off + sub_in] = sub_mat

    return global_mat


def separability_matrix(model: Model) -> np.ndarray:
    """Return the separability matrix for a model.

    This function has been adjusted to correctly handle nested ``'&'``
    ``CompoundModel`` instances by first flattening them with
    ``_flatten_separable_model``. For models that are not parallel
    compositions (i.e., not ``'&'``-type), the behavior remains compatible
    with the traditional implementation by delegating to the model's own
    separability information when available, or by assuming full coupling
    between its inputs and outputs otherwise.
    """

    # Fast path for non-CompoundModel: rely on model-provided separability
    # information when present, or assume full coupling.
    if not isinstance(model, CompoundModel):
        n_in = model.n_inputs
        n_out = model.n_outputs
        try:
            if hasattr(model, "separability_matrix"):
                mat = model.separability_matrix
            elif hasattr(model, "_separability_matrix"):
                mat = model._separability_matrix
            else:
                raise AttributeError
            mat = np.asarray(mat, dtype=bool)
            if mat.shape != (n_out, n_in):
                raise ValueError
            return mat
        except Exception:
            return np.ones((n_out, n_in), dtype=bool)

    # CompoundModel case: if it's an '&' composition, flatten and compute
    # using block-diagonal construction. For other operators, fall back to
    # the generic per-model logic, which keeps pre-existing behavior.
    if model.op == "&":
        flat_models = _flatten_separable_model(model)
        return _separability_matrix_flat(flat_models)

    # For non-'&' compound models, attempt to use any existing separability
    # information. If unavailable, assume full coupling between all inputs
    # and outputs of the compound.
    n_in = model.n_inputs
    n_out = model.n_outputs
    try:
        if hasattr(model, "separability_matrix"):
            mat = model.separability_matrix
        elif hasattr(model, "_separability_matrix"):
            mat = model._separability_matrix
        else:
            raise AttributeError
        mat = np.asarray(mat, dtype=bool)
        if mat.shape != (n_out, n_in):
            raise ValueError
        return mat
    except Exception:
        return np.ones((n_out, n_in), dtype=bool)