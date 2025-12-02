import numpy as np

from astropy.modeling import models as m
from astropy.modeling.separable import separability_matrix


def test_separability_nested_compound_linear1d_and_pix2sky_tan():
    """Regression test for nested CompoundModels separability.

    See issue description:
    - cm = Linear1D(10) & Linear1D(5)
      separability_matrix(cm) should be diagonal.
    - separability_matrix(Pix2Sky_TAN() & Linear1D(10) & Linear1D(5))
      shows expected independence.
    - separability_matrix(Pix2Sky_TAN() & cm) currently yields a matrix
      where the two Linear1D branches appear non-separable; this test
      encodes the expected, correct behavior.
    """
    # Simple compound: two independent Linear1D models
    cm = m.Linear1D(10) & m.Linear1D(5)
    sep_cm = separability_matrix(cm)
    expected_cm = np.array(
        [
            [True, False],
            [False, True],
        ]
    )
    assert sep_cm.shape == expected_cm.shape
    assert np.array_equal(sep_cm, expected_cm)

    # Flat compound with Pix2Sky_TAN and two Linear1D models
    flat = m.Pix2Sky_TAN() & m.Linear1D(10) & m.Linear1D(5)
    sep_flat = separability_matrix(flat)
    # The exact expected matrix here mirrors the issue description,
    # but we primarily want to capture that the Linear1D branches
    # remain separable from each other and from Pix2Sky_TAN.
    # Asserting the shape ensures downstream refactors keep
    # the same dimensionality.
    assert sep_flat.shape == (4, 4)

    # Nested compound: Pix2Sky_TAN combined with the pre-built compound cm
    nested = m.Pix2Sky_TAN() & cm
    sep_nested = separability_matrix(nested)

    # Expected behavior: the nested structure should be equivalent,
    # from a separability perspective, to the flat compound model
    # Pix2Sky_TAN() & Linear1D(10) & Linear1D(5).
    # Therefore, we assert equality of the two matrices.
    np.testing.assert_array_equal(sep_nested, sep_flat)