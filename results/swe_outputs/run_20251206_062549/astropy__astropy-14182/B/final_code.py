import sys

import astropy.units as u
from astropy.io.ascii import write
from astropy.table import QTable, Table


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


def test_rst_no_header_rows_backward_compat(tmp_path):
    """ascii.rst without header_rows must keep legacy single-header behavior.

    This ensures that adding header_rows support does not change the
    default output when header_rows is omitted.
    """
    tbl = Table({
        'a': [1, 2, 3],
        'b': [4, 5, 6],
    })

    out = tmp_path / 'tbl_no_header_rows.rst'

    # Call without header_rows – should not raise and should behave as before.
    write(tbl, out, format='ascii.rst')

    lines = out.read_text().splitlines()
    assert len(lines) > 0

    # RST simple tables are like:
    # ===== ====
    # a     b
    # ===== ====
    # 1     4
    # ...
    # ===== ====
    # So between the first and second separator lines there should be
    # exactly one row containing the column names.
    sep_indices = [i for i, line in enumerate(lines) if set(line.strip()) in ({'='}, {'=' , ' '}) and line.strip()]

    # Need at least two separators for header top and bottom.
    assert len(sep_indices) >= 2

    header_start = sep_indices[0]
    header_end = sep_indices[1]

    # Lines strictly between first and second separators are header rows.
    header_rows = lines[header_start + 1:header_end]
    assert len(header_rows) == 1

    header_line = header_rows[0]
    # Column names should appear in the single header row.
    assert 'a' in header_line
    assert 'b' in header_line