import numpy as np

from astropy.io.fits.util import encode_ascii


def some_function_handling_output_field(format, output_field):
    """Handle FITS record output field formatting for floating-point exponents.

    Parameters
    ----------
    format : str
        The FITS format specifier for the field. If this contains the
        character ``'D'``, the function ensures that any exponential notation
        in ``output_field`` uses ``'D'`` instead of ``'E'`` as the exponent
        separator, matching FITS conventions for double-precision values.
    output_field : numpy.ndarray or numpy.chararray
        Array-like object containing the textual representation of the field
        values. This is expected to support ``.replace(old, new)`` and return
        a new array when called.

    Returns
    -------
    numpy.ndarray or numpy.chararray
        The (potentially) modified ``output_field`` with exponent separators
        normalized according to the provided format.
    """

    # ... other logic operating on output_field ...

    # Replace exponent separator in floating point numbers. Note that
    # ``numpy.chararray.replace`` is not in-place and returns a new array,
    # so we must assign the result back to ``output_field``.
    if 'D' in format:
        output_field = output_field.replace(encode_ascii('E'), encode_ascii('D'))

    # ... rest of the function that returns or uses output_field ...
    return output_field