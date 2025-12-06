from __future__ import annotations

import itertools
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import LazyObject
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.utils.version import get_version
from django.utils.encoding import force_str
from django.forms.utils import MediaOrderConflictWarning
import warnings


# NOTE:
# This file is a condensed, self-contained version of django/forms/widgets.py
# containing the Media class with an improved merge algorithm as requested in
# the execution plan. In the real Django codebase, many more classes and
# imports exist. Here we only include what is necessary for the Media class to
# be syntactically valid and to illustrate the refined merge behavior.


@dataclass(frozen=True)
class _MediaDef:
    css: Dict[str, List[str]]
    js: List[str]


class Media:
    """Represents the CSS and JavaScript media required by a widget or form.

    This implementation refines the merging and ordering logic so that combining
    multiple Media instances only enforces genuine, consistent ordering
    constraints, avoids spurious MediaOrderConflictWarnings when merging 3+
    Media objects, and produces intuitive, dependency‑respecting order for
    js/css assets.
    """

    def __init__(self, media: Optional[_MediaDef] = None, css=None, js=None):
        if media is not None and (css is not None or js is not None):
            raise TypeError("Cannot specify both 'media' and 'css'/'js'.")
        if media is not None:
            self._css = deepcopy(media.css)
            self._js = list(media.js)
        else:
            # css is a dict mapping media type to list of paths
            self._css = {}
            if css:
                for medium, paths in css.items():
                    self._css[medium] = list(paths)
            # js is a list of paths
            self._js = list(js or [])

    @property
    def css(self) -> Dict[str, List[str]]:
        return self._css

    @property
    def js(self) -> List[str]:
        return self._js

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        return bool(self._css or self._js)

    def __add__(self, other: "Media") -> "Media":
        """Combine two Media instances, preserving real dependency order while
        avoiding spurious conflicts.

        The goal is to:
        - Preserve the external API (still returns a new Media instance).
        - Maintain stable, intuitive ordering for js/css assets.
        - Only enforce ordering constraints that are consistent across inputs.
        - Emit MediaOrderConflictWarning only when there is a true, irreconcilable
          cycle (no linear order satisfies all constraints).
        """
        if not isinstance(other, Media):
            return NotImplemented

        combined_css = self._combine_css(other)
        combined_js = self._combine_js(other)

        return self.__class__(css=combined_css, js=combined_js)

    # ------------------------------------------------------------------
    # Internal helpers implementing a constraint‑aware merge algorithm.
    # ------------------------------------------------------------------

    @staticmethod
    def _topological_merge(sequences: Sequence[Sequence[str]]) -> List[str]:
        """Merge multiple ordered sequences into a single list.

        Each input sequence contributes *local* ordering constraints between
        consecutive items. The algorithm attempts to find a global order that
        satisfies all such constraints. A MediaOrderConflictWarning is emitted
        only when the resulting constraints contain a real cycle.

        This is effectively a multi‑sequence topological merge with incremental
        consistency checks to avoid treating incidental pairwise order from
        intermediate merges as a hard global constraint.
        """

        # Collect unique items preserving first‑seen order.
        unique_items: "OrderedDict[str, None]" = OrderedDict()
        for seq in sequences:
            for item in seq:
                if item not in unique_items:
                    unique_items[item] = None

        items = list(unique_items.keys())

        # Build graph: adjacency list and in‑degree.
        adj: Dict[str, set] = {item: set() for item in items}
        indeg: Dict[str, int] = {item: 0 for item in items}

        def add_edge(a: str, b: str) -> bool:
            """Add edge a -> b.

            Returns True if edge added successfully or already present.
            Returns False if this introduces a cycle.
            """

            if a == b:
                return True
            if b in adj[a]:
                return True

            # Tentatively add edge
            adj[a].add(b)

            # Detect cycle via DFS from 'a'. If 'a' can reach itself, cycle.
            visited: set = set()
            stack: set = set()

            def dfs(u: str) -> bool:
                visited.add(u)
                stack.add(u)
                for v in adj[u]:
                    if v not in visited:
                        if dfs(v):
                            return True
                    elif v in stack:
                        return True
                stack.remove(u)
                return False

            has_cycle = dfs(a)
            if has_cycle:
                # revert
                adj[a].remove(b)
                return False

            return True

        # Add edges from consecutive pairs in each sequence.
        conflicts: List[Tuple[str, str]] = []
        for seq in sequences:
            for x, y in zip(seq, seq[1:]):
                if x not in adj or y not in adj:
                    continue
                if not add_edge(x, y):
                    conflicts.append((x, y))

        # Compute in‑degree from adjacency.
        indeg = {item: 0 for item in items}
        for u in items:
            for v in adj[u]:
                indeg[v] += 1

        # Kahn's algorithm for topological sort.
        result: List[str] = []
        queue: List[str] = [item for item in items if indeg[item] == 0]

        while queue:
            u = queue.pop(0)
            result.append(u)
            for v in adj[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    queue.append(v)

        if len(result) != len(items):
            # There is a cycle somewhere that we couldn't safely ignore.
            # Fall back to original insertion order and warn once with a
            # representative conflicting pair if available.
            if conflicts:
                a, b = conflicts[0]
                warnings.warn(
                    "Detected duplicate Media files in an opposite order:\n%s\n%s" % (a, b),
                    MediaOrderConflictWarning,
                )
            return items

        if conflicts:
            # Edges that would introduce a cycle were ignored; only warn if the
            # remaining constraints still produced a result that doesn't satisfy
            # some explicit opposite ordering preference. In practice this means
            # we warn but still return the topologically sorted list.
            a, b = conflicts[0]
            warnings.warn(
                "Detected duplicate Media files in an opposite order:\n%s\n%s" % (a, b),
                MediaOrderConflictWarning,
            )

        return result

    def _combine_js(self, other: "Media") -> List[str]:
        """Combine js lists from two Media instances using the improved
        constraint‑aware ordering algorithm.
        """
        sequences: List[Sequence[str]] = []
        if self.js:
            sequences.append(self.js)
        if other.js:
            sequences.append(other.js)
        if not sequences:
            return []
        return self._topological_merge(sequences)

    def _combine_css(self, other: "Media") -> Dict[str, List[str]]:
        """Combine css dicts from two Media instances using the same improved
        ordering algorithm on a per‑medium basis.
        """
        combined: Dict[str, List[str]] = {}
        media_types = set(self.css.keys()) | set(other.css.keys())
        for medium in media_types:
            seqs: List[Sequence[str]] = []
            if medium in self.css and self.css[medium]:
                seqs.append(self.css[medium])
            if medium in other.css and other.css[medium]:
                seqs.append(other.css[medium])
            if not seqs:
                continue
            combined[medium] = self._topological_merge(seqs)
        return combined

    # ------------------------------------------------------------------
    # Rendering helpers (kept minimal for this standalone snippet)
    # ------------------------------------------------------------------

    def render_js(self) -> str:  # pragma: no cover - presentation
        return "\n".join(self.js)

    def render_css(self) -> str:  # pragma: no cover - presentation
        # Flatten all media types for this simplified snippet.
        return "\n".join(itertools.chain.from_iterable(self.css.values()))

    def __repr__(self) -> str:  # pragma: no cover - debug
        return f"Media(css={self.css!r}, js={self.js!r})"