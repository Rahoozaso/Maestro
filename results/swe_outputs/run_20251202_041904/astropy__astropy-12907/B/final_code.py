import numpy as np

from astropy.modeling import models as m
from astropy.modeling.separable import separability_matrix


def test_separability_linear_pair_flat():
    cm = m.Linear1D(10) & m.Linear1D(5)
    mat = separability_matrix(cm)
    expected = np.array([[True, False],
                         [False, True]])
    assert mat.shape == expected.shape
    assert np.array_equal(mat, expected)


def test_separability_pix2sky_and_linears_flat():
    cm = m.Pix2Sky_TAN() & m.Linear1D(10) & m.Linear1D(5)
    mat = separability_matrix(cm)
    expected = np.array([[True, True, False, False],
                         [True, True, False, False],
                         [False, False, True, False],
                         [False, False, False, True]])
    assert mat.shape == expected.shape
    assert np.array_equal(mat, expected)


def test_separability_pix2sky_and_linears_nested():
    # Regression test for nested compound case:
    # cm = Linear1D(10) & Linear1D(5)
    # separability_matrix(Pix2Sky_TAN() & cm) should match the flat composition
    flat_model = m.Pix2Sky_TAN() & m.Linear1D(10) & m.Linear1D(5)
    nested_cm = m.Linear1D(10) & m.Linear1D(5)
    nested_model = m.Pix2Sky_TAN() & nested_cm

    flat_mat = separability_matrix(flat_model)
    nested_mat = separability_matrix(nested_model)

    # They should be identical if nested compound models are handled correctly
    assert nested_mat.shape == flat_mat.shape
    assert np.array_equal(nested_mat, flat_mat)