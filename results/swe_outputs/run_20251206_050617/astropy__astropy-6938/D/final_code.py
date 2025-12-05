import numpy as np

from astropy.io.fits.util import encode_ascii


def some_function_handling_output_field(format, output_field):
    """Handle FITS formatting for an output field, correcting D exponents.

    Parameters
    ----------
    format : str
        The FITS format string. If it contains the character ``'D'``,
        floating-point exponents in ``output_field`` are written with
        ``'D'`` instead of ``'E'``.

    output_field : numpy.ndarray or numpy.chararray
        Array-like object containing the textual representation of the
        field values (typically a NumPy chararray) whose exponent markers
        may need to be adjusted.

    Returns
    -------
    output_field : numpy.ndarray or numpy.chararray
        The same type as the input ``output_field``, with any occurrences
        of ``'E'`` in the exponent position replaced by ``'D'`` when
        ``'D'`` is present in ``format``.
    """

    # ... other logic operating on output_field ...

    # Replace exponent separator in floating point numbers. Note that
    # numpy.chararray.replace is not in-place and returns a new array.
    if 'D' in format:
        output_field = output_field.replace(encode_ascii('E'), encode_ascii('D'))

    # ... rest of the function that returns or uses output_field ...
    return output_field