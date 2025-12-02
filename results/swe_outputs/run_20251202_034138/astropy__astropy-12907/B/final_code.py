import numpy as np

from astropy.modeling import models as m
from astropy.modeling.separable import separability_matrix


def test_separability_simple_parallel():
    cm = m.Linear1D(10) & m.Linear1D(5)
    mat = separability_matrix(cm)
    expected = np.array([[True, False],
                         [False, True]])
    assert mat.shape == expected.shape
    assert np.array_equal(mat, expected)


def test_separability_complex_parallel():
    model = m.Pix2Sky_TAN() & m.Linear1D(10) & m.Linear1D(5)
    mat = separability_matrix(model)
    expected = np.array([[True, True, False, False],
                         [True, True, False, False],
                         [False, False, True, False],
                         [False, False, False, True]])
    assert mat.shape == expected.shape
    assert np.array_equal(mat, expected)


def test_separability_nested_parallel():
    cm = m.Linear1D(10) & m.Linear1D(5)
    model = m.Pix2Sky_TAN() & cm
    mat = separability_matrix(model)

    # The nested form should be separability-equivalent to the
    # non-nested form: Pix2Sky_TAN() & Linear1D(10) & Linear1D(5).
    expected = np.array([[True, True, False, False],
                         [True, True, False, False],
                         [False, False, True, False],
                         [False, False, False, True]])
    assert mat.shape == expected.shape
    assert np.array_equal(mat, expected)