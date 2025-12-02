from __future__ import annotations

"""Placeholder module: astropy.modeling.separable

NOTE FOR MAINTAINERS / CALLERS
------------------------------
This file is a stub produced because the execution plan only requested
*obtaining* the real source context (REQUEST_SOURCE_CONTEXT) and did not
specify any concrete code modifications.

In the real astropy repository this module contains the implementation of
``separability_matrix`` and related helpers. To actually fix the nested
CompoundModel separability bug, run this tool again with the real
``astropy/modeling/separable.py`` content provided as input.

The minimal shim below is only present so that this file is syntactically
valid Python and can be imported without immediately failing. It does *not*
implement the true astropy behavior.
"""

from typing import Any

import numpy as np


def separability_matrix(model: Any) -> np.ndarray:
    """Minimal placeholder for :func:`astropy.modeling.separable.separability_matrix`.

    Parameters
    ----------
    model : Any
        A modeling object. In real astropy this is typically a ``Model`` or
        ``CompoundModel`` instance.

    Returns
    -------
    ndarray
        A 1x1 array with ``True``.

    Notes
    -----
    This is a *stub* implementation. It does **not** compute the actual
    separability properties of the model and is present only so that imports
    succeed in environments where the real astropy source was not provided to
    this tool.
    """

    # Placeholder behavior: claim a single fully-separable input/output.
    # The real implementation in astropy is significantly more complex.
    return np.array([[True]], dtype=bool)