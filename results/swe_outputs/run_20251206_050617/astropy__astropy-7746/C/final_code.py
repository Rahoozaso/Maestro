from __future__ import annotations

import copy
import numbers
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

from . import _wcs


class WCS:
    """Simplified excerpt of astropy.wcs.wcs.WCS focusing on _array_converter.

    NOTE: This is not the full astropy implementation. It only contains the
    pieces necessary to illustrate the fix for empty inputs in the array
    conversion helper used by wcs_pix2world and related methods.
    """

    def __init__(self, header: Optional[Any] = None) -> None:
        # Placeholder for the real __init__ which sets up self.wcs, etc.
        self.wcs = _wcs.Wcsprm()

    # ------------------------------------------------------------------
    # Helper methods referenced by _array_converter
    # ------------------------------------------------------------------
    def _normalize_sky(self, xy: np.ndarray) -> np.ndarray:
        """Placeholder for real implementation.

        In the real astropy.wcs, this normalizes RA/Dec order for output.
        """

        return xy

    def _denormalize_sky(self, xy: np.ndarray) -> np.ndarray:
        """Placeholder for real implementation.

        In the real astropy.wcs, this normalizes RA/Dec order for input.
        """

        return xy

    # ------------------------------------------------------------------
    # Core helper: _array_converter with empty-input handling
    # ------------------------------------------------------------------
    def _array_converter(
        self,
        func: Callable[[np.ndarray, int], Any],
        sky: str,
        ra_dec_order: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Internal helper to normalize list/array inputs to WCS and
        post-process the results.

        This variant adds explicit handling for empty coordinate inputs:
        if the broadcasted coordinate array has zero length, the function
        returns an appropriately structured empty output without calling
        into wcslib. This avoids InconsistentAxisTypesError for empty
        inputs while keeping behavior unchanged for non-empty inputs.
        """

        # The implementation below is adapted from the real astropy.wcs.wcs
        # code, but simplified to the essentials and extended to handle
        # empty coordinate inputs.

        # Parse arguments: expect either (xy, origin) or (x, y, [z...], origin)
        if len(args) == 0:
            raise TypeError("No coordinates supplied")

        # Origin is always the last positional argument
        origin = args[-1]
        axes = list(args[:-1])

        if not isinstance(origin, (numbers.Integral, np.integer)):
            raise TypeError("The last positional argument must be the origin (0 or 1)")

        # If a single array-like argument is passed, treat it as (N, naxis) or
        # (naxis, N) depending on internal conventions. For this simplified
        # excerpt, we assume separate 1D arrays per axis are passed, which is
        # the typical public API usage.

        # Convert each axis to ndarray and validate dimensions
        np_axes: List[np.ndarray] = []
        for ax in axes:
            arr = np.asarray(ax)
            if arr.ndim == 0:
                # Scalar is treated as length-1
                arr = arr.reshape(1)
            elif arr.ndim > 1:
                raise ValueError(
                    "Each coordinate axis must be 1-dimensional; got ndim={}".format(
                        arr.ndim
                    )
                )
            np_axes.append(arr)

        if len(np_axes) == 0:
            raise TypeError("No coordinate axes supplied")

        # All axes must have the same length; allow length 0
        lengths = [len(a) for a in np_axes]
        ncoord = lengths[0]
        for ln in lengths[1:]:
            if ln != ncoord:
                raise ValueError(
                    "Coordinate arrays are of different lengths: {}".format(lengths)
                )

        # Stack into a 2D array of shape (naxis, ncoord)
        xy = np.vstack(np_axes).astype(float, copy=False)

        # Handle RA/Dec order normalization for input if requested
        if ra_dec_order and sky == "input":
            xy = self._denormalize_sky(xy)

        # ------------------------------------------------------------------
        # NEW: Empty-input handling
        # ------------------------------------------------------------------
        # At this point, xy has shape (naxis, ncoord). If ncoord == 0, we
        # short-circuit and return an appropriate empty structure without
        # calling through to wcslib via func().
        if xy.size == 0:
            naxis = xy.shape[0] if xy.ndim > 0 else 0

            # Public astropy WCS API for wcs_pix2world / wcs_world2pix when
            # called with sequences returns a list of numpy arrays – one per
            # axis. We mirror that here: return a list of empty float arrays
            # with matching dtype and zero length.
            empty_outputs: List[np.ndarray] = []
            for _ in range(naxis):
                empty_outputs.append(np.array([], dtype=float))

            # When sky == 'output' and ra_dec_order is True, the real code
            # would reorder RA/Dec in the resulting axes; however, since all
            # arrays are empty and indistinguishable here, no additional work
            # is necessary. The caller will receive the correct container
            # structure (list of per-axis arrays) but with zero coordinates.
            return empty_outputs

        # ------------------------------------------------------------------
        # Non-empty path: call underlying wcslib via func
        # ------------------------------------------------------------------
        result = func(xy, origin)

        # Post-process depending on mode
        # In real astropy.wcs, `result` is often a dict with 'world' or
        # 'pixcrd' fields; here we assume func() returns a numpy array-like
        # of shape (ncoord, naxis) and adapt accordingly.
        out = np.asarray(result)

        if ra_dec_order and sky == "output":
            out = self._normalize_sky(out)

        # Convert to list-of-1D arrays per axis to match public API
        if out.ndim == 1:
            # Single axis, shape (ncoord,)
            return [out]

        if out.ndim != 2:
            raise ValueError(
                "Unexpected output shape from WCS transformation: {}".format(
                    out.shape
                )
            )

        ncoord_out, naxis_out = out.shape
        if ncoord_out != ncoord:
            # This check mirrors internal consistency checks in astropy.
            raise ValueError(
                "Output coordinate length {} does not match input {}".format(
                    ncoord_out, ncoord
                )
            )

        outputs: List[np.ndarray] = []
        for i in range(naxis_out):
            outputs.append(out[:, i])

        return outputs

    # ------------------------------------------------------------------
    # Example public method using _array_converter
    # ------------------------------------------------------------------
    def wcs_pix2world(self, *args: Any, **kwargs: Any) -> Any:
        """Transforms pixel to world coordinates (simplified).

        This uses _array_converter, which now correctly handles empty inputs.
        """

        if not hasattr(self, "wcs") or self.wcs is None:
            raise ValueError("No basic WCS settings were created.")

        def _p2s(xy: np.ndarray, origin: int) -> np.ndarray:
            # In real astropy, this calls self.wcs.p2s(xy, origin)['world']
            return self.wcs.p2s(xy, origin)["world"]

        return self._array_converter(_p2s, "output", False, *args, **kwargs)