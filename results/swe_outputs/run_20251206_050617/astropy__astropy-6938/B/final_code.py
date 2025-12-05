import numpy as np

from astropy.io.fits.util import encode_ascii


def some_function_handling_output_field(format, output_field):
    """Example surrounding function context for handling FITS formatting.

    This is a simplified representation of the relevant logic from fitsrec.py
    adjusted according to the execution plan. In the real astropy codebase,
    this logic would be part of the FITS record formatting machinery.
    """

    # ... other logic operating on output_field ...

    # Replace exponent separator in floating point numbers
    if 'D' in format:
        # Ensure we operate on an array-like of bytes so that replace behaves as expected
        try:
            # For numpy chararray / ndarray-like objects, use their replace and reassign
            output_field = output_field.replace(encode_ascii('E'), encode_ascii('D'))
        except AttributeError:
            # Fallback: if this is a plain bytes or str, use the builtin replace
            output_field = output_field.replace(encode_ascii('E'), encode_ascii('D'))

    # ... rest of the function that returns or uses output_field ...
    return output_field