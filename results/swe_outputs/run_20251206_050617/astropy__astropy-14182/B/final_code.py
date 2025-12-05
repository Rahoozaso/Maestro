from typing import List, Any

from astropy.io import ascii
from astropy.io.ascii import core
from astropy import units as u


class RST(core.BasicWriter):
    """RestructuredText table writer.

    This writer outputs a simple grid table suitable for embedding in
    reStructuredText documents. It supports an optional ``header_rows``
    keyword (e.g. ["name", "unit"]) to add extra header rows similar to
    the FixedWidth writers.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the RST writer.

        Parameters
        ----------
        header_rows : list of str, optional
            Names of table attributes to use as additional header rows.
            For example, ``["name", "unit"]`` will add header rows for the
            column names and units. If not provided, the writer behaves as
            before and only outputs the standard name header.

        Other keyword parameters are passed through to ``BasicWriter``.
        """
        # Extract header_rows if present but do not break if it is absent.
        # This is what allows calls like ``tbl.write(..., format='ascii.rst',
        # header_rows=["name", "unit"])`` without a TypeError.
        self.header_rows = kwargs.pop("header_rows", None)

        # Initialize the base class with the remaining kwargs to preserve
        # existing behavior and configuration.
        super().__init__(**kwargs)

    def _format_col(self, col, value) -> str:
        """Format a single table cell value as a string.

        This mirrors the basic behaviour of other ascii writers, using the
        column formatter machinery when available.
        """
        if hasattr(col.info, "formatter") and col.info.formatter is not None:
            return col.info.formatter(value)

        fmt = col.info.format
        if fmt is None:
            return ascii.strings.masked_to_string(value, col.info)
        return fmt.format(value)

    def _get_header_rows(self, table) -> List[List[str]]:
        """Return a list of header rows to write for the table.

        Each row is a list of strings, one per column. The first header
        row is always the column names. Additional rows are constructed
        based on ``self.header_rows`` if provided, following the
        FixedWidth-style convention (e.g., "unit" uses ``col.unit``).
        """

        # Base name header (existing behaviour).
        header = [col.info.name for col in table.columns.values()]
        header_rows: List[List[str]] = [header]

        if self.header_rows:
            for attr in self.header_rows:
                # Skip the built‑in name row since it is always present.
                if attr == "name":
                    continue

                values: List[str] = []
                for col in table.columns.values():
                    if attr == "unit":
                        unit = getattr(col, "unit", None)
                        if unit in (None, u.dimensionless_unscaled):
                            values.append("")
                        else:
                            values.append(str(unit))
                    else:
                        # Generic attribute or Column.info field.
                        val = getattr(col.info, attr, None)
                        if val is None and hasattr(col, attr):
                            val = getattr(col, attr)
                        values.append("" if val is None else str(val))

                header_rows.append(values)

        return header_rows

    def write(self, table) -> None:
        """Write the table as a reStructuredText simple table.

        This implementation extends the original behavior by optionally
        adding extra header rows from ``self.header_rows``. When
        ``header_rows`` is not provided, output is unchanged from the
        previous implementation (a single name header row).
        """

        # Compute header rows: first the main header, then any extras.
        header_rows = self._get_header_rows(table)

        # Combine header and data rows into a single matrix of strings.
        data_rows: List[List[str]] = []
        for row in table:
            data_rows.append(
                [
                    self._format_col(col, row[col.info.name])
                    for col in table.columns.values()
                ]
            )

        all_rows = header_rows + data_rows

        # Determine column widths.
        n_cols = len(table.columns)
        col_widths = [0] * n_cols
        for row in all_rows:
            for i, val in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(val)))

        def border(sep_char: str = "=") -> str:
            """Return an RST simple-table border line using ``sep_char``."""
            # For RST simple tables, borders are continuous strings of
            # ``sep_char`` separated by single spaces.
            return " ".join(sep_char * w for w in col_widths)

        lines: List[str] = []
        # Top border.
        lines.append(border("="))

        # Header rows (names + optional extra header rows).
        for i, hrow in enumerate(header_rows):
            line = " ".join(
                str(val).ljust(col_widths[j]) for j, val in enumerate(hrow)
            )
            lines.append(line)
            # After the last header row, repeat the border.
            if i == len(header_rows) - 1:
                lines.append(border("="))

        # Data rows.
        for drow in data_rows:
            line = " ".join(
                str(val).ljust(col_widths[j]) for j, val in enumerate(drow)
            )
            lines.append(line)

        # Bottom border.
        lines.append(border("="))

        self.write_lines(lines)