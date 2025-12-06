import os
from typing import List, Optional, Tuple

import numpy as np

from astropy.io import ascii
from astropy.table import Table, Column


class QDPError(Exception):
    """Custom exception for QDP parsing errors.

    Raised when a QDP file cannot be parsed according to the limited
    functionality implemented by :class:`QDPReader`.
    """


class QDPReader:
    """Simple QDP file reader with basic support for READ, READ SERR, and READ TERR.

    This lightweight reader is a minimal stand-in that implements just
    enough of the QDP parsing behavior to exercise regression tests for
    case-insensitive command parsing. In the real Astropy codebase, the
    corresponding logic lives in :mod:`astropy.io.ascii.qdp` and provides a
    more feature-complete implementation.

    The key behavior illustrated here is that QDP directive recognition is
    performed in a *case-insensitive* way, so commands such as ``READ``,
    ``READ SERR``, and ``READ TERR`` are accepted regardless of their
    capitalization (e.g., ``read serr 1 2``).

    Notes
    -----
    * Data lines (non-directive, non-comment lines) are interpreted as
      whitespace-separated numeric columns.
    * ``READ SERR i j`` assumes symmetric errors are provided in the
      immediate next columns for the specified value columns.
    * ``READ TERR`` handling is included only as a placeholder and mirrors
      the dispatch style of ``READ SERR`` but is not fully exercised by the
      regression tests.
    """

    def __init__(self) -> None:
        """Initialize an empty QDPReader instance.

        The reader maintains internal state describing the current READ
        mode (plain values, symmetric errors, or placeholder for
        asymmetric errors), along with any configured column indices for
        error handling.
        """
        self._data_lines: List[str] = []
        self._read_mode: str = "READ"  # "READ", "READ_SERR", or "READ_TERR"
        self._serr_cols: Tuple[int, int] = ()
        self._terr_cols: Tuple[int, int] = ()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def read(self, filename: str) -> Table:
        """Read a QDP file from disk and return its contents as a Table.

        Parameters
        ----------
        filename : str
            Path to the QDP file to be read.

        Returns
        -------
        astropy.table.Table
            A table containing the numeric data from the QDP file. Column
            names follow a simple convention: ``c1``, ``c2``, ... for value
            columns, with additional columns such as ``c1err`` appended when
            symmetric error columns are present via ``READ SERR``.
        """
        with open(filename, "r") as fh:
            for raw_line in fh:
                self._parse_line(raw_line)
        return self._build_table()

    # ------------------------------------------------------------------
    # Line parsing
    # ------------------------------------------------------------------
    def _parse_line(self, line: str) -> None:
        """Parse a single line from a QDP file.

        This method implements case-insensitive recognition of QDP
        directives. Comment lines (starting with ``!``) and blank lines are
        ignored. Any non-directive, non-comment lines are treated as table
        data and stored for later conversion into numeric rows.

        Parameters
        ----------
        line : str
            Raw line read from the QDP file, including any trailing
            newline characters.
        """

        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("!"):
            # Blank or comment
            return

        # Directives in QDP are case-insensitive. Normalize only for
        # directive recognition; keep the original for downstream parsing.
        upper_line = line_stripped.upper()

        # Recognized commands. Only a small subset is supported here, but
        # the key point is that the matching is case-insensitive.
        if upper_line.startswith("READ SERR"):
            self._handle_read_serr(line_stripped)
        elif upper_line.startswith("READ TERR"):
            self._handle_read_terr(line_stripped)
        elif upper_line.startswith("READ"):
            self._handle_read(line_stripped)
        else:
            # If it's not a recognized directive, treat it as data.
            # This mirrors the behavior of a typical QDP parser where
            # non-command, non-comment lines are table rows.
            self._data_lines.append(line_stripped)

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def _handle_read(self, line: str) -> None:
        """Handle a generic ``READ`` directive.

        For this minimal implementation we only switch to plain ``READ``
        mode and do not interpret additional options in the directive
        itself.

        Parameters
        ----------
        line : str
            The directive line, as read (preserving original case).
        """

        self._read_mode = "READ"
        # No column index specification for basic READ.
        self._serr_cols = ()
        self._terr_cols = ()

    def _handle_read_serr(self, line: str) -> None:
        """Handle a ``READ SERR`` directive.

        QDP syntax is typically ``READ SERR i j`` where ``i`` and ``j`` are
        1-based indices of the *value* columns that have symmetric errors
        provided in subsequent columns of the data.

        Parameters
        ----------
        line : str
            The directive line, as read (case preserved).

        Raises
        ------
        QDPError
            If fewer than two column indices are supplied or if the
            indices cannot be parsed as integers.
        """

        self._read_mode = "READ_SERR"
        tokens = line.split()
        # Expected forms like: READ SERR 1 2   (possibly with extra args)
        if len(tokens) < 4:
            raise QDPError(f"READ SERR directive requires at least two column indices: {line}")
        try:
            # 1-based indices of value columns with errors
            i = int(tokens[2])
            j = int(tokens[3])
        except ValueError as exc:
            raise QDPError(f"Invalid column indices in READ SERR directive: {line}") from exc
        self._serr_cols = (i, j)

    def _handle_read_terr(self, line: str) -> None:
        """Handle a ``READ TERR`` directive.

        This is provided mainly for completeness and to mirror the
        case-insensitive dispatch style of :meth:`_handle_read_serr`. The
        current minimal implementation records the specified value column
        indices but does not construct explicit asymmetric error columns in
        the output table.

        Parameters
        ----------
        line : str
            The directive line, as read (case preserved).

        Raises
        ------
        QDPError
            If fewer than two column indices are supplied or if the
            indices cannot be parsed as integers.
        """

        self._read_mode = "READ_TERR"
        tokens = line.split()
        if len(tokens) < 4:
            raise QDPError(f"READ TERR directive requires at least two column indices: {line}")
        try:
            i = int(tokens[2])
            j = int(tokens[3])
        except ValueError as exc:
            raise QDPError(f"Invalid column indices in READ TERR directive: {line}") from exc
        self._terr_cols = (i, j)

    # ------------------------------------------------------------------
    # Table construction
    # ------------------------------------------------------------------
    def _build_table(self) -> Table:
        """Build an :class:`~astropy.table.Table` from collected data lines.

        Returns
        -------
        astropy.table.Table
            A table with one column per numeric field in the data lines.
            Column names are ``c1``, ``c2``, ... for value columns, with
            additional ``cNerr`` columns appended when symmetric error
            handling via ``READ SERR`` has been requested.

        Raises
        ------
        QDPError
            If non-numeric data are encountered in a data row or if there
            are insufficient columns available for the configured symmetric
            error columns.
        """
        if not self._data_lines:
            return Table()

        # Split all data lines into numeric tokens
        rows: List[List[float]] = []
        for ln in self._data_lines:
            if not ln:
                continue
            try:
                row = [float(tok) for tok in ln.split()]
            except ValueError as exc:
                raise QDPError(f"Non-numeric data in QDP table row: {ln}") from exc
            rows.append(row)

        arr = np.array(rows, dtype=float)
        ncols = arr.shape[1]

        # Build base value columns: c1, c2, ...
        cols: List[Column] = []
        for i in range(ncols):
            cols.append(Column(arr[:, i], name=f"c{i+1}"))

        # Attach symmetric error columns if requested.
        if self._read_mode == "READ_SERR" and self._serr_cols:
            # QDP convention: for each value column that has symmetric
            # errors, the next column in the data contains its error.
            # Here we mirror that simplified mapping.
            for idx in self._serr_cols:
                val_col_idx = idx - 1  # 1-based to 0-based
                err_col_idx = val_col_idx + 1
                if err_col_idx >= ncols:
                    raise QDPError(
                        "Not enough columns for symmetric errors: "
                        f"value column {idx} has no corresponding error column."
                    )
                err_name = f"c{idx}err"
                cols.append(Column(arr[:, err_col_idx], name=err_name))

        # NOTE: READ_TERR handling is omitted for brevity; similar logic
        # would be added for asymmetric errors.

        return Table(cols)


# Convenience function mimicking Table.read(..., format='ascii.qdp')

def read_qdp(filename: str) -> Table:
    """Read a QDP file and return its contents as an Astropy Table.

    This is a convenience wrapper around :class:`QDPReader` intended to
    mimic the user-facing behavior of ``Table.read(..., format='ascii.qdp')``
    for the limited feature set implemented here.

    Parameters
    ----------
    filename : str
        Path to the QDP file to be read.

    Returns
    -------
    astropy.table.Table
        The parsed table constructed from the QDP file.
    """
    reader = QDPReader()
    return reader.read(filename)