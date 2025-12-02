import numpy as np

from astropy.modeling.core import CompoundModel


__all__ = ["_flatten_parallel_model", "separability_matrix"]


def _flatten_parallel_model(model):
    """Return a flattened list of submodels for nested parallel (&) CompoundModels.

    This helper is specifically intended for separability analysis. It walks a
    model tree and, for any CompoundModel created via '&', it yields its
    components recursively, so that nested parallel structures such as
    ``Pix2Sky_TAN() & (Linear1D(10) & Linear1D(5))`` are treated as a single
    flat parallel composition.
    """
    # Non-compound models are leaves.
    if not isinstance(model, CompoundModel):
        return [model]

    # Only flatten the parallel operator '&'; for other operators, treat the
    # CompoundModel as a single node, since its inputs/outputs may be coupled
    # in non-trivial ways.
    if getattr(model, "op", None) != "&":
        return [model]

    flattened = []

    # Prefer using traverse_postorder if available to walk the tree.
    if hasattr(model, "traverse_postorder"):
        for submodel in model.traverse_postorder(include_self=False):
            if isinstance(submodel, CompoundModel) and getattr(submodel, "op", None) == "&":
                # Nested parallel: recurse and extend.
                if hasattr(submodel, "left") and hasattr(submodel, "right"):
                    flattened.extend(_flatten_parallel_model(submodel.left))
                    flattened.extend(_flatten_parallel_model(submodel.right))
                else:
                    # Fallback: treat as a leaf if structure is unknown.
                    flattened.append(submodel)
            elif not isinstance(submodel, CompoundModel):
                # Leaf model inside parallel tree.
                flattened.append(submodel)
    # Fallback in case traverse_postorder is not available or yields nothing.
    if not flattened:
        if hasattr(model, "left") and hasattr(model, "right"):
            flattened.extend(_flatten_parallel_model(model.left))
            flattened.extend(_flatten_parallel_model(model.right))
        else:
            flattened.append(model)

    return flattened


def separability_matrix(model):
    """Return a boolean separability matrix for a model.

    This version fixes incorrect behavior for nested parallel ("&")
    CompoundModels by flattening such structures prior to computing the
    separability relationships. For example, ``Pix2Sky_TAN() & cm`` where
    ``cm = Linear1D(10) & Linear1D(5)`` should yield a block-diagonal-like
    separability matrix equivalent to the non-nested case
    ``Pix2Sky_TAN() & Linear1D(10) & Linear1D(5)``.
    """
    # --- New: flatten nested parallel structures for analysis ---
    flat_models = _flatten_parallel_model(model)

    # Compute number of inputs and outputs per flattened submodel. This is
    # deliberately conservative: if a submodel has multiple inputs or
    # outputs, we treat them as potentially non-separable within that
    # submodel, but still separable from other parallel branches.
    in_counts = []
    out_counts = []
    for m in flat_models:
        in_counts.append(getattr(m, "n_inputs", 1))
        out_counts.append(getattr(m, "n_outputs", 1))

    total_in = sum(in_counts)
    total_out = sum(out_counts)

    mat = np.zeros((total_out, total_in), dtype=bool)

    in_offset = 0
    out_offset = 0
    for nin, nout in zip(in_counts, out_counts):
        # Within each parallel branch, conservatively assume all its outputs
        # depend on all its inputs. The crucial fix is that these blocks are
        # placed on the diagonal only, making branches independent of each
        # other.
        mat[out_offset : out_offset + nout, in_offset : in_offset + nin] = True
        in_offset += nin
        out_offset += nout

    return mat