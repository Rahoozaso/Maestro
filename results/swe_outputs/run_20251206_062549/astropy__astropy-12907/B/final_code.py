import numpy as np

from astropy.modeling import models as m
from astropy.modeling.separable import separability_matrix


def test_separability_simple_linear_pair():
    """Regression test for a simple pair of 1D linear models combined with '&'.

    This reflects the example from the GitHub issue::

        from astropy.modeling import models as m
        from astropy.modeling.separable import separability_matrix
        cm = m.Linear1D(10) & m.Linear1D(5)
        separability_matrix(cm)
        # expected:
        # array([[ True, False],
        #        [False,  True]])
    """
    cm = m.Linear1D(10) & m.Linear1D(5)
    mat = separability_matrix(cm)
    expected = np.array([[True, False],
                         [False, True]])
    assert mat.shape == expected.shape
    assert np.array_equal(mat, expected)


def test_separability_flat_complex_compound():
    """Regression test for a flat '&'-chained CompoundModel.

    Mirrors the example::

        separability_matrix(m.Pix2Sky_TAN() & m.Linear1D(10) & m.Linear1D(5))
        # expected:
        # array([[ True,  True, False, False],
        #        [ True,  True, False, False],
        #        [False, False,  True, False],
        #        [False, False, False,  True]])
    """
    cm = m.Pix2Sky_TAN() & m.Linear1D(10) & m.Linear1D(5)
    mat = separability_matrix(cm)
    expected = np.array([
        [True, True, False, False],
        [True, True, False, False],
        [False, False, True, False],
        [False, False, False, True],
    ])
    assert mat.shape == expected.shape
    assert np.array_equal(mat, expected)


def test_separability_nested_compound_model():
    """Regression test for nested CompoundModels combined with '&'.

    This is the failing case from the issue::

        inner = m.Linear1D(10) & m.Linear1D(5)
        cm = m.Pix2Sky_TAN() & inner
        separability_matrix(cm)
        # expected:
        # array([[ True,  True, False, False],
        #        [ True,  True, False, False],
        #        [False, False,  True, False],
        #        [False, False, False,  True]])
    """
    inner = m.Linear1D(10) & m.Linear1D(5)
    cm = m.Pix2Sky_TAN() & inner
    mat = separability_matrix(cm)
    expected = np.array([
        [True, True, False, False],
        [True, True, False, False],
        [False, False, True, False],
        [False, False, False, True],
    ])
    assert mat.shape == expected.shape
    assert np.array_equal(mat, expected)