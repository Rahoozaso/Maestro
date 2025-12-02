from __future__ import annotations

from typing import List
import numpy as np

from astropy.modeling import Model


def _model_input_output_slices(model: Model) -> List[slice]:
    """Return slices mapping each leaf submodel's outputs in the flattened model.

    For a compound model that may contain nested compound models, ``Model._leaflist``
    gives a flat list of the non-compound leaf models in left-to-right order.
    This helper computes, for each leaf model, the slice into the *output* axis
    of the full compound model corresponding to that leaf's outputs.

    This is used as the basis for computing the separability matrix in a way that
    is robust to arbitrary nesting of compound models.
    """

    # Flatten into leaf models and compute cumulative output sizes
    leaf_models = model._leaflist
    n_outputs_per_leaf = [m.n_outputs for m in leaf_models]
    cum_outputs = np.cumsum([0] + n_outputs_per_leaf)

    output_slices: List[slice] = []
    for i in range(len(leaf_models)):
        start = int(cum_outputs[i])
        stop = int(cum_outputs[i + 1])
        output_slices.append(slice(start, stop))

    return output_slices


def separability_matrix(model: Model) -> np.ndarray:
    """Compute separability matrix for possibly nested compound models.

    This implementation is intended to correctly handle nested ``CompoundModel``
    instances by operating on the flattened list of leaf submodels.  Two outputs
    are considered separable if they ultimately depend on disjoint subsets of the
    model inputs.

    Parameters
    ----------
    model : `astropy.modeling.core.Model`
        The model for which to compute separability.

    Returns
    -------
    ndarray
        A boolean array of shape ``(n_outputs, n_outputs)`` where element
        ``[i, j]`` is ``True`` if outputs ``i`` and ``j`` are separable.
    """

    # Base case: a single, non-compound model; fall back to its implementation
    if not hasattr(model, "_leaflist") or len(model._leaflist) == 1:
        # Many core models implement ``separable`` or similar logic; for those
        # that do not, conservatively mark everything as non-separable
        if hasattr(model, "_separable"):
            return model._separable

        nout = model.n_outputs
        return np.eye(nout, dtype=bool)

    # Compute separability on the flattened leaf models.  We build a block-
    # diagonal matrix where each block is the separability matrix of a leaf.
    leaf_models = model._leaflist
    leaf_seps: List[np.ndarray] = []

    for leaf in leaf_models:
        if hasattr(leaf, "_separable"):
            leaf_seps.append(leaf._separable)
        else:
            nout = leaf.n_outputs
            leaf_seps.append(np.eye(nout, dtype=bool))

    # Assemble block-diagonal separability over all leaf outputs
    total_outputs = int(sum(lsep.shape[0] for lsep in leaf_seps))
    sep_full = np.zeros((total_outputs, total_outputs), dtype=bool)

    current = 0
    for block in leaf_seps:
        size = block.shape[0]
        sep_full[current : current + size, current : current + size] = block
        current += size

    # At this stage, sep_full describes separability between *leaf outputs*. But
    # in typical compound models (| and & composition), the global outputs are
    # exactly the concatenation of leaf outputs in left-to-right order, so this
    # is also the correct separability matrix for the global model.
    #
    # However, we explicitly compute the relation through slices in case future
    # composition types introduce reordering of outputs.
    output_slices = _model_input_output_slices(model)
    n_global_outputs = int(sum(s.stop - s.start for s in output_slices))

    separability = np.zeros((n_global_outputs, n_global_outputs), dtype=bool)

    # Map leaf-output separability into global-output indices
    for leaf_idx_i, slice_i in enumerate(output_slices):
        for leaf_idx_j, slice_j in enumerate(output_slices):
            # If any output of leaf i is inseparable from any output of leaf j,
            # mark corresponding global outputs as inseparable.
            block = sep_full[output_slices[leaf_idx_i], output_slices[leaf_idx_j]]
            if np.all(block):
                separability[slice_i, slice_j] = True

    return separability