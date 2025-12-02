import numpy as np

from astropy.modeling import models as m
from astropy.modeling.separable import separability_matrix


def test_separability_simple_compound_linear1d():
    """Regression test: basic separability for a simple `&` CompoundModel.

    cm = Linear1D(10) & Linear1D(5)
    The two 1D models should be fully separable: each input only affects its own
    output, so the separability matrix is diagonal.
    """
    cm = m.Linear1D(10) & m.Linear1D(5)

    sep = separability_matrix(cm)

    expected = np.array([[True, False],
                         [False, True]])

    assert isinstance(sep, np.ndarray)
    assert sep.shape == expected.shape
    assert sep.dtype == bool
    assert np.array_equal(sep, expected)


def test_separability_nested_compound_pix2sky_tan_and_linear1d():
    """Regression test for nested CompoundModels separability.

    This encodes the scenario from the issue:

    * Non-nested: Pix2Sky_TAN() & Linear1D(10) & Linear1D(5)
      produces a separability matrix where the 2D Pix2Sky_TAN part is
      independent of each of the two 1D Linear models, and the 1D models
      are independent of each other.

    * Nested: Pix2Sky_TAN() & (Linear1D(10) & Linear1D(5))
      previously produced an incorrect separability matrix where the two
      Linear1D components were treated as non-separable from each other.

    The nested form should have the same separability structure as the
    non-nested one: the two Linear1D components must remain mutually
    separable/independent, and each should be independent of the Pix2Sky_TAN
    component.
    """
    # First, demonstrate the expected behavior in the non-nested case.
    non_nested = m.Pix2Sky_TAN() & m.Linear1D(10) & m.Linear1D(5)
    sep_non_nested = separability_matrix(non_nested)

    # Pix2Sky_TAN has 2 inputs / 2 outputs, and we then add two 1D models.
    # The expected pattern (taken from the issue description) is:
    # [[ True,  True, False, False],
    #  [ True,  True, False, False],
    #  [False, False,  True, False],
    #  [False, False, False,  True]]
    expected_non_nested = np.array(
        [
            [True, True, False, False],
            [True, True, False, False],
            [False, False, True, False],
            [False, False, False, True],
        ]
    )

    assert isinstance(sep_non_nested, np.ndarray)
    assert sep_non_nested.shape == expected_non_nested.shape
    assert sep_non_nested.dtype == bool
    assert np.array_equal(sep_non_nested, expected_non_nested)

    # Now, the nested case that previously behaved incorrectly.
    cm = m.Linear1D(10) & m.Linear1D(5)
    nested = m.Pix2Sky_TAN() & cm

    sep_nested = separability_matrix(nested)

    # The separability structure must match the non-nested form: nesting the
    # `&` CompoundModel should not change which inputs/outputs are separable.
    expected_nested = expected_non_nested

    assert isinstance(sep_nested, np.ndarray)
    assert sep_nested.shape == expected_nested.shape
    assert sep_nested.dtype == bool
    assert np.array_equal(sep_nested, expected_nested)