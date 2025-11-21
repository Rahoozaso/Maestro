import numpy as np
from astropy.modeling import models as m
from astropy.modeling.separable import separability_matrix

def test_nested_parallel_separability():
    cm = m.Linear1D(10) & m.Linear1D(5)

    # Baseline: two independent 1D models are separable (diagonal)
    expected_cm = np.array([[True, False],
                            [False, True]], dtype=bool)
    assert np.array_equal(separability_matrix(cm), expected_cm)

    # Non-nested sanity: TAN (2->2) in parallel with two 1D models
    whole = m.Pix2Sky_TAN() & m.Linear1D(10) & m.Linear1D(5)
    expected_whole = np.array([[True, True,  False, False],
                               [True, True,  False, False],
                               [False, False, True,  False],
                               [False, False, False, True ]], dtype=bool)
    assert np.array_equal(separability_matrix(whole), expected_whole)

    # Nested case: previously incorrect; should match non-nested expectation
    nested = m.Pix2Sky_TAN() & cm
    got = separability_matrix(nested)
    assert np.array_equal(got, expected_whole), f"Unexpected separability:\n{got}\nExpected:\n{expected_whole}"