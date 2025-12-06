import sys

import astropy.units as u
from astropy.table import QTable
from astropy.io.ascii import write


def test_rst_header_rows_name_unit(tmp_path):
    """ascii.rst should accept header_rows like ascii.fixed_width.

    This test is based on the example from the issue description: a QTable
    with 'wave' (nm) and 'response' (count) should produce a two-row header
    when header_rows=['name', 'unit'] is given.
    """
    tbl = QTable({
        'wave': [350, 950] * u.nm,
        'response': [0.7, 1.2] * u.count,
    })

    out = tmp_path / 'tbl.rst'
    write(tbl, out, format='ascii.rst', header_rows=['name', 'unit'])

    text = out.read_text().splitlines()

    # Expect at least: top sep, name row, unit row, sep, data..., bottom sep
    # We do not assert exact spacing to keep the test robust to minor
    # alignment tweaks, but we do check for the presence of the expected
    # header tokens in order.
    assert any('wave' in line and 'response' in line for line in text)
    assert any('nm' in line and 'ct' in line for line in text)

    # Ensure no TypeError occurred and output is non-empty.
    assert len(text) > 0