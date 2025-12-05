import numpy as np
import pytest

from astropy.modeling import models as m
from astropy.modeling.separable import separability_matrix


def test_simple_parallel_linear_models_separable():
    """Regression test for separability of two simple parallel Linear1D models.

    This corresponds to::

        cm = m.Linear1D(10) & m.Linear1D(5)

    The separability matrix is expected to be a 2x2 diagonal matrix with
    ``True`` on the diagonal and ``False`` off-diagonal.
    """

    cm = m.Linear1D(10) & m.Linear1D(5)

    mat = separability_matrix(cm)

    expected = np.array([[True, False],
                         [False, True]])

    assert mat.shape == (2, 2)
    assert np.array_equal(mat, expected)


def test_complex_parallel_model_with_pix2sky_tan_and_linears():
    """Ensure separability for Pix2Sky_TAN in parallel with two Linear1D models.

    This matches the non-nested example in the issue description::

        separability_matrix(m.Pix2Sky_TAN() & m.Linear1D(10) & m.Linear1D(5))

    Expected:

    ``Pix2Sky_TAN`` (2D -> 2D) is independent from each 1D ``Linear1D`` model,
    and the two ``Linear1D`` models are independent of each other, yielding::

        array([[ True,  True, False, False],
               [ True,  True, False, False],
               [False, False,  True, False],
               [False, False, False,  True]])
    """

    model = m.Pix2Sky_TAN() & m.Linear1D(10) & m.Linear1D(5)

    mat = separability_matrix(model)

    expected = np.array([[True, True, False, False],
                         [True, True, False, False],
                         [False, False, True, False],
                         [False, False, False, True]])

    assert mat.shape == (4, 4)
    assert np.array_equal(mat, expected)


def test_nested_compound_model_same_as_non_nested():
    """Nested compound model should have same separability as equivalent flat model.

    The regression case from the issue::

        cm = m.Linear1D(10) & m.Linear1D(5)
        separability_matrix(m.Pix2Sky_TAN() & cm)

    This should produce the same separability matrix as the non-nested::

        separability_matrix(m.Pix2Sky_TAN() & m.Linear1D(10) & m.Linear1D(5))
    """

    cm = m.Linear1D(10) & m.Linear1D(5)

    nested = m.Pix2Sky_TAN() & cm
    flat = m.Pix2Sky_TAN() & m.Linear1D(10) & m.Linear1D(5)

    nested_mat = separability_matrix(nested)
    flat_mat = separability_matrix(flat)

    # Shapes must be identical
    assert nested_mat.shape == flat_mat.shape == (4, 4)

    # And all entries must match exactly
    assert np.array_equal(nested_mat, flat_mat)