import numpy as np
import pytest

from astropy.nddata import NDDataRef


class TestNDDataRefMaskPropagation:

    def setup_method(self):
        self.array = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]])
        self.mask = np.array([[0, 1, 64], [8, 0, 1], [2, 1, 0]])
        self.nref_nomask = NDDataRef(self.array)
        self.nref_mask = NDDataRef(self.array, mask=self.mask)

    def test_no_mask_times_constant(self):
        # no mask * no mask -> no mask
        result = self.nref_nomask.multiply(1.0, handle_mask=np.bitwise_or)
        assert result.mask is None

    def test_no_mask_times_no_mask(self):
        # no mask * no mask -> no mask
        result = self.nref_nomask.multiply(self.nref_nomask, handle_mask=np.bitwise_or)
        assert result.mask is None

    def test_mask_times_constant_propagates_mask(self):
        # mask * no mask -> existing mask should be propagated without error
        result = self.nref_mask.multiply(1.0, handle_mask=np.bitwise_or)
        assert result.mask is not None
        np.testing.assert_array_equal(result.mask, self.mask)

    def test_mask_times_mask_combines_with_bitwise_or(self):
        # mask * mask -> masks combined via bitwise_or, but since they
        # are identical here, the result should equal the original mask
        result = self.nref_mask.multiply(self.nref_mask, handle_mask=np.bitwise_or)
        np.testing.assert_array_equal(result.mask, self.mask)

    def test_mask_times_no_mask_other_order_propagates_mask(self):
        # mask * no mask where the NDDataRef without a mask is the operand
        result = self.nref_mask.multiply(self.nref_nomask, handle_mask=np.bitwise_or)
        assert result.mask is not None
        np.testing.assert_array_equal(result.mask, self.mask)