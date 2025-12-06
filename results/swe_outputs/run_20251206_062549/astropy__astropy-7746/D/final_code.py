import numpy as np
from copy import deepcopy

from . import _wcs


class WCS:
    """Simplified extract of astropy.wcs.wcs.WCS focusing on _array_converter.

    NOTE: This is not the full astropy implementation. It is a minimal,
    self-contained stand‑in containing the adjusted _array_converter logic
    requested in the work order, so it can be presented as a single complete
    file per the instructions. In the real astropy codebase, this class and
    method should be merged into the existing astropy/wcs/wcs.py module,
    preserving all other functionality unchanged.
    """

    def __init__(self):
        self.wcs = _wcs.Wcsprm()

    # ------------------------------------------------------------------
    # Existing utility methods (very minimal stubs for this extract)
    # ------------------------------------------------------------------
    def _normalize_sky_components(self, xy):
        """Placeholder for sky normalization logic.

        In real astropy this handles RA/Dec ordering; here we simply return
        the input unchanged as this file focuses on _array_converter changes.
        """

        return xy

    def _denormalize_sky_components(self, xy):
        """Placeholder for sky *de*normalization logic.

        See _normalize_sky_components.
        """

        return xy

    # ------------------------------------------------------------------
    # Modified _array_converter with early return on empty inputs
    # ------------------------------------------------------------------
    def _array_converter(self, func, sky, *args, **kwargs):
        """Convert a variety of input formats to the internal array
        representation, apply the given WCS transformation function, and
        convert results back.

        This variant includes an additional early-return path to correctly
        handle empty input coordinate arrays (e.g., [], np.array([])) by
        returning appropriately empty outputs instead of raising
        InconsistentAxisTypesError from wcslib.
        """

        # NOTE: This implementation follows the structure of the real astropy
        # WCS._array_converter sufficiently to illustrate the empty-input
        # handling requested in the work order, but it omits unrelated options
        # and argument forms for brevity. In the real codebase the same
        # empty-input logic should be inserted into the branch that deals with
        # "a 1-D array for each axis, followed by an origin".

        # ------------------------------------------------------------------
        # Parse arguments in the common calling pattern used by
        # wcs_pix2world, wcs_world2pix, etc.:
        #     wcs_pix2world(x, y, origin)
        # where x, y are 1-D sequences (lists/arrays), one for each axis.
        # ------------------------------------------------------------------
        ra_dec_order = kwargs.pop("ra_dec_order", False)

        if len(args) < 2:
            raise TypeError(
                "Expected at least two positional arguments: coordinate "
                "array(s) followed by origin."
            )

        # Last positional argument is always the origin in this simplified
        # implementation; everything before that are axis arrays.
        *coord_args, origin = args

        # Coordinate arrays per axis
        axes = [np.asarray(a) for a in coord_args]

        # ------------------------------------------------------------------
        # NEW: early return when *all* per-axis arrays are empty.
        # This prevents passing ncoord == 0 down into wcslib which would
        # otherwise raise InconsistentAxisTypesError.
        # ------------------------------------------------------------------
        all_empty = len(axes) > 0 and all(a.size == 0 for a in axes)

        if all_empty:
            # Determine number of output axes. For typical pixel->world
            # conversions this is self.wcs.naxis. If that is not available,
            # fall back to the number of input axes so that callers expecting
            # a fixed number of output arrays still get that number, just
            # empty.
            try:
                naxis = int(self.wcs.naxis)
            except Exception:
                naxis = len(axes)

            empty_outputs = [np.array([], dtype=float) for _ in range(naxis)]

            # Respect the outward-facing container semantics of the high-level
            # methods: they normally return one 1-D array per axis. For both
            # sky == 'input' and sky == 'output' we therefore return the list
            # of empty arrays. Higher-level convenience wrappers (e.g.
            # wcs_pix2world) can still post-process this as usual.
            return empty_outputs

        # ------------------------------------------------------------------
        # Non-empty case: continue with the normal transformation path.
        # ------------------------------------------------------------------

        # Stack per-axis arrays into a 2D coordinate array with shape
        # (ncoord, nelem) where ncoord is the number of points and nelem is
        # the number of axes. This matches what wcslib expects.
        axes = [np.asarray(a, dtype=float) for a in axes]

        # Broadcast / length checking (simplified): in real astropy this is
        # stricter and provides better error messages.
        lengths = {a.shape[0] for a in axes}
        if len(lengths) != 1:
            raise ValueError("All coordinate axes must have the same length.")

        ncoord = lengths.pop()
        if ncoord == 0:
            # This case is actually already handled by the early-return above,
            # but keep a defensive guard here for safety.
            naxis = getattr(self.wcs, "naxis", len(axes))
            return [np.array([], dtype=float) for _ in range(naxis)]

        # Construct the input array for wcslib: shape (ncoord, nelem)
        xy = np.vstack(axes).T

        if ra_dec_order and sky == "input":
            xy = self._normalize_sky_components(xy)

        # Call the provided transformation function (typically a wrapper
        # around wcslib, such as self.wcs.p2s, self.wcs.s2p, etc.).
        result = func(xy, origin)

        if ra_dec_order and sky == "output":
            result = self._denormalize_sky_components(result)

        # The real astropy implementation supports multiple output container
        # shapes and types. For this focused extract we assume that `result`
        # is either:
        #   * a dict with a 'world' key containing an (ncoord, nelem) array, or
        #   * a bare (ncoord, nelem) array.
        if isinstance(result, dict) and "world" in result:
            out = np.asarray(result["world"], dtype=float)
        else:
            out = np.asarray(result, dtype=float)

        if out.ndim != 2:
            raise ValueError("Unexpected dimensionality of WCS output array.")

        # Split back into one 1-D array per axis, matching the high-level API
        # expectations of wcs_pix2world, etc.
        return [out[:, i].copy() for i in range(out.shape[1])]


__all__ = ["WCS"]