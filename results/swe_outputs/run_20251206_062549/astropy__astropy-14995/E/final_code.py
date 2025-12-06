from __future__ import annotations

"""NDData arithmetic mixin utilities.

This module provides helpers for arithmetic operations on NDData-like
objects. The main focus here is the mask-combination helper used by
NDDataRef and NDArithmeticMixin when performing arithmetic.

The implementation restores the pre-5.3 behavior for the case where one
operand has no mask, and ensures that user-provided ``handle_mask``
functions (such as ``np.bitwise_or``) are never called with ``None``.
"""

from typing import Any, Callable, Optional

import numpy as np
import numpy.ma as ma


def _combine_masks(
    mask_a: Any,
    mask_b: Any,
    handle_mask: Optional[Callable[[Any, Any], Any]] = None,
) -> Any:
    """Combine two masks for NDData arithmetic.

    This helper encapsulates the rules for combining masks associated with
    two operands in NDData arithmetic operations. It restores the behavior
    prior to astropy 5.3 for the case where one operand has no mask and
    ensures that user-provided ``handle_mask`` functions (e.g.
    ``np.bitwise_or``) are never called with ``None``.

    Parameters
    ----------
    mask_a, mask_b : array-like, bool/int, None, or ``np.ma.nomask``
        Masks associated with the two operands. "No mask" for an operand
        must be represented here as ``None`` or ``np.ma.nomask``.

    handle_mask : callable or None, optional
        Function to combine two masks when both are present, e.g.
        ``np.bitwise_or``. If ``None``, a default bitwise-or combination
        is used for the case where both operands have masks.

    Returns
    -------
    combined_mask : array-like, None, or ``np.ma.nomask``
        The resulting mask for the arithmetic operation. If both operands
        effectively lack a mask, ``None`` is returned so that the result
        instance has no mask attribute.

    Notes
    -----
    Rules implemented (to restore the v5.2-like behavior and avoid
    ``TypeError`` when using ``handle_mask=np.bitwise_or``):

    * If both operands have no mask -> return ``None`` (result has no mask).
    * If exactly one operand has a mask -> propagate that mask to the
      result (no call to ``handle_mask``).
    * If both operands have masks -> if ``handle_mask`` is provided, call it
      on the two masks and return the result; otherwise fall back to a
      bitwise-or combination using ``np.bitwise_or``.

    This ensures that an operand without a mask is treated as *absence* of
    a mask, not as a value to be passed into ``handle_mask``.
    """

    def _is_no_mask(m: Any) -> bool:
        """Return True if *m* represents absence of a mask.

        Both ``None`` and ``np.ma.nomask`` are treated as "no mask".
        """

        return m is None or m is ma.nomask

    no_mask_a = _is_no_mask(mask_a)
    no_mask_b = _is_no_mask(mask_b)

    # Case 1: neither operand has a mask -> result has no mask
    if no_mask_a and no_mask_b:
        return None

    # Case 2: only one operand has a mask -> propagate that mask directly
    if no_mask_a and not no_mask_b:
        return mask_b
    if no_mask_b and not no_mask_a:
        return mask_a

    # Case 3: both operands have masks -> combine them
    if handle_mask is not None:
        # Both masks are non-None and not ``np.ma.nomask`` here,
        # so the handler (e.g. np.bitwise_or) will not see None.
        return handle_mask(mask_a, mask_b)

    # Fallback behavior if no handle_mask is given. Historically,
    # NDDataRef often used bitwise OR for combining pixel-wise masks,
    # so keep that as a sensible default.
    return np.bitwise_or(mask_a, mask_b)