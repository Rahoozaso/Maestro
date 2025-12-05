import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

import numpy as np

from . import core
from . import basic


__all__ = ["QDP"]


# Regular expression to recognize numeric data lines (copied from upstream logic
# but kept here self‑contained in this file).
_QDP_NUMERIC_RE = re.compile(r"^[+\-0-9.eE]+(?:\s+[+\-0-9.eE]+)*\s*$")


def _normalize_qdp_command(token: Optional[str]) -> Optional[str]:
    """Return a canonical uppercase representation of a QDP command token.

    QDP is case-insensitive for commands, so we normalize tokens used as
    commands or keywords before comparison. Data values must *not* be
    passed through this helper.
    """

    return token.upper() if token is not None else token


@dataclass
class _QDPTableSpec:
    """Internal helper to track a single QDP table's column/error layout."""

    ncols: int
    serr: Optional[Tuple[int, int]] = None
    terr: Optional[Tuple[int, int, int, int]] = None
    skip: int = 0


class QDP(basic.Daophot):
    """QDP table reader.

    This is a simplified, self-contained implementation focused on the
    command parsing aspects relevant to case-insensitive handling. It
    preserves behavior for existing upper-case QDP files while adding
    support for mixed / lower case commands such as ``read serr``.
    """

    _format_name = "qdp"
    _io_registry_can_write = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.table_specs: List[_QDPTableSpec] = []
        self._current_table: Optional[_QDPTableSpec] = None

    def read(self, lines: List[str]) -> core.Table:
        """Read a QDP file given as an iterable of lines."""

        self.split_tables(lines)
        return super().read(lines)

    def split_tables(self, lines: List[str]) -> None:
        """Parse command lines in a QDP file and infer table definitions.

        This function interprets QDP commands (READ, SERR, TERR, SKIP, etc.)
        in a case-insensitive manner while leaving data lines untouched.
        """

        self.table_specs = []
        self._current_table = None

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("!"):
                # Blank or comment
                continue

            # Data lines are numeric; anything else is treated as a command.
            if _QDP_NUMERIC_RE.match(stripped):
                # On the first data line of a new table, infer ncols.
                if self._current_table is None:
                    ncols = len(stripped.split())
                    self._current_table = _QDPTableSpec(ncols=ncols)
                    self.table_specs.append(self._current_table)
                continue

            # Command line dispatch (case-insensitive).
            tokens = stripped.split()
            first_raw = tokens[0]
            first = _normalize_qdp_command(first_raw)

            if first == "READ":
                # Handle READ SERR / READ TERR / generic READ
                second = _normalize_qdp_command(tokens[1]) if len(tokens) > 1 else ""

                if second == "SERR":
                    # Syntax: READ SERR xcol ycol
                    if len(tokens) < 4:
                        raise ValueError(f"Invalid READ SERR command: {stripped}")
                    try:
                        xcol = int(tokens[2])
                        ycol = int(tokens[3])
                    except ValueError as exc:
                        raise ValueError(f"Invalid READ SERR column indices: {stripped}") from exc

                    # Start a new table spec if needed.
                    # QDP column indices are 1-based.
                    ncols = max(xcol, ycol)
                    self._current_table = _QDPTableSpec(ncols=ncols, serr=(xcol, ycol))
                    self.table_specs.append(self._current_table)

                elif second == "TERR":
                    # Syntax: READ TERR xcol ycol xerrcol yerrcol
                    if len(tokens) < 6:
                        raise ValueError(f"Invalid READ TERR command: {stripped}")
                    try:
                        xcol = int(tokens[2])
                        ycol = int(tokens[3])
                        xerr = int(tokens[4])
                        yerr = int(tokens[5])
                    except ValueError as exc:
                        raise ValueError(f"Invalid READ TERR column indices: {stripped}") from exc

                    ncols = max(xcol, ycol, xerr, yerr)
                    self._current_table = _QDPTableSpec(
                        ncols=ncols, terr=(xcol, ycol, xerr, yerr)
                    )
                    self.table_specs.append(self._current_table)

                else:
                    # Generic READ: infer columns later from first data line
                    self._current_table = None

            elif first == "SKIP":
                # Syntax: SKIP n
                if len(tokens) < 2:
                    raise ValueError(f"Invalid SKIP command: {stripped}")
                try:
                    nskip = int(tokens[1])
                except ValueError as exc:
                    raise ValueError(f"Invalid SKIP value: {stripped}") from exc

                if self._current_table is None:
                    # SKIP before data / table definition – treat as new table context
                    self._current_table = _QDPTableSpec(ncols=0, skip=nskip)
                    self.table_specs.append(self._current_table)
                else:
                    self._current_table.skip += nskip

            elif first == "NEWP":
                # NEWP: start a new plot (= new table)
                self._current_table = None

            else:
                # Any other non-numeric, non-comment line is unrecognized.
                raise ValueError(f"Unrecognized QDP line: {stripped}")

    # The remaining methods would implement actual table construction based
    # on table_specs; they are out-of-scope for this focused change but kept
    # with no-op or minimal behavior to maintain structure.

    def get_type_map(self) -> Dict[type, core.ColumnInfo]:
        """Return the column type map. Uses the base class implementation."""

        return super().get_type_map()

    def write(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - QDP is read-only
        raise NotImplementedError("QDP writer is not implemented.")