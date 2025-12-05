import numpy as np

from astropy.modeling import models as m
from astropy.modeling.separable import separability_matrix


def test_separability_nested_parallel_compoundmodels():
    """Regression test for nested parallel CompoundModels in separability_matrix.

    See issue: Modeling's separability_matrix does not compute separability
    correctly for nested CompoundModels.
    """
    cm = m.Linear1D(10) & m.Linear1D(5)

    non_nested = m.Pix2Sky_TAN() & m.Linear1D(10) & m.Linear1D(5)
    nested = m.Pix2Sky_TAN() & cm

    mat_non_nested = separability_matrix(non_nested)
    mat_nested = separability_matrix(nested)

    # The shapes should match
    assert mat_non_nested.shape == mat_nested.shape

    # And the matrices themselves should be identical
    assert np.array_equal(mat_non_nested, mat_nested)

    # Additionally, check that the two Linear1D components are separable
    # from the Pix2Sky_TAN part, as in the original non-nested case.
    # This is a sanity check that the overall pattern remains as expected.
    assert mat_non_nested[0, 2] is False
    assert mat_non_nested[0, 3] is False
    assert mat_non_nested[2, 0] is False
    assert mat_non_nested[3, 0] is False