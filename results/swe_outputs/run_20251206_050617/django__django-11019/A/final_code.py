import itertools
import warnings
from collections import defaultdict, OrderedDict, deque
from copy import deepcopy
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import Promise
from django.utils.html import escape, format_html, html_safe
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


class MediaOrderConflictWarning(UserWarning):
    pass


@html_safe
class Media:
    """Class for handling media definitions on widgets.

    This is the same public API as Django's standard Media class, but with a
    refined merge algorithm that bases ordering conflicts on explicit
    constraints only, avoiding spurious MediaOrderConflictWarning emissions
    when merging 3 or more Media objects.
    """

    def __init__(self, media=None, **kwargs):
        if media is not None:
            css = getattr(media, 'css', {})
            js = getattr(media, 'js', [])
        else:
            css = kwargs.pop('css', {})
            js = kwargs.pop('js', [])
        if kwargs:
            raise TypeError("Unknown keyword arguments for Media: %s" % list(kwargs))
        # Internal normalized representations.
        self._css: Dict[str, List[Any]] = {}
        self._js: List[Any] = []
        self._media_conflict_cache: Set[Tuple[str, Tuple[Any, Any]]] = set()

        # Normalize css: mapping medium -> list
        if isinstance(css, (list, tuple)):
            # Backwards-compatible: css=['base.css'] means 'all'
            if css:
                self._css['all'] = list(css)
        elif isinstance(css, dict):
            for medium, paths in css.items():
                self._css[medium] = list(paths)
        else:
            raise TypeError('css must be dict or list/tuple')

        # Normalize js: list
        self._js = list(js)

    @property
    def css(self) -> Dict[str, List[Any]]:
        return self._css

    @property
    def js(self) -> List[Any]:
        return self._js

    def __str__(self) -> str:
        return self.render()

    def __bool__(self) -> bool:  # Python 3 compatibility
        return bool(self._css or self._js)

    def __add__(self, other: 'Media') -> 'Media':
        if not isinstance(other, Media):
            return NotImplemented

        new = Media()
        # Copy current normalized structures.
        new._css = {}
        new._js = []
        # Merge conflict caches so we don't warn repeatedly for same pair.
        seen_conflicts: Set[Tuple[str, Tuple[Any, Any]]] = set()
        seen_conflicts.update(getattr(self, '_media_conflict_cache', set()))
        seen_conflicts.update(getattr(other, '_media_conflict_cache', set()))

        # Merge JS
        new_js, seen_conflicts = _merge_media_lists(
            self._js,
            other._js,
            seen_conflicts,
            label='js',
        )
        new._js = new_js

        # Merge CSS per medium.
        combined_css: Dict[str, List[Any]] = {}
        all_media_types = set(self._css.keys()) | set(other._css.keys())
        for medium in all_media_types:
            base_list = self._css.get(medium, [])
            other_list = other._css.get(medium, [])
            merged, seen_conflicts = _merge_media_lists(
                base_list,
                other_list,
                seen_conflicts,
                label=f'css[{medium}]',
            )
            if merged:
                combined_css[medium] = merged
        new._css = combined_css

        new._media_conflict_cache = seen_conflicts
        return new

    def __radd__(self, other: 'Media') -> 'Media':
        # Allow sum() with start=Media()
        if other == 0:
            return self
        if not isinstance(other, Media):
            return NotImplemented
        return other.__add__(self)

    # The remaining methods (render, absolute_paths, etc.) would be identical
    # to Django's standard implementation. They are omitted here for brevity
    # since the work order focuses on merge logic. In a real codebase this
    # class body would continue with the usual rendering helpers.

    def render(self) -> str:
        """Render all media as HTML tags."""
        return '\n'.join(itertools.chain(self.render_css(), self.render_js()))

    def render_js(self) -> List[str]:
        return [
            format_html('<script src="{}"></script>', escape(path))
            for path in self._js
        ]

    def render_css(self) -> List[str]:
        lines: List[str] = []
        for medium, paths in self._css.items():
            for path in paths:
                if medium:
                    lines.append(
                        format_html(
                            '<link href="{}" type="text/css" media="{}" rel="stylesheet">',
                            escape(path),
                            escape(medium),
                        )
                    )
                else:
                    lines.append(
                        format_html(
                            '<link href="{}" type="text/css" rel="stylesheet">',
                            escape(path),
                        )
                    )
        return lines


def _stable_topological_sort(
    nodes: Sequence[Any],
    edges: Iterable[Tuple[Any, Any]],
    base_preference: Sequence[Any],
) -> List[Any]:
    """Stable topological sort.

    - nodes: iterable of unique items.
    - edges: iterable of (a, b) meaning a < b.
    - base_preference: sequence whose order we try to preserve among all
      valid topological orders.

    Raises ValueError on cycles.
    """
    # Build adjacency and indegree.
    adjacency: Dict[Any, Set[Any]] = defaultdict(set)
    indegree: Dict[Any, int] = {n: 0 for n in nodes}
    for a, b in edges:
        if a == b:
            continue
        if b not in indegree or a not in indegree:
            continue
        if b not in adjacency[a]:
            adjacency[a].add(b)
            indegree[b] += 1

    # Use Kahn's algorithm with stable selection using base_preference then
    # fallback to original nodes order.
    preference_index: Dict[Any, int] = {}
    for idx, item in enumerate(base_preference):
        if item not in preference_index:
            preference_index[item] = idx
    base_max = len(base_preference)
    for idx, item in enumerate(nodes):
        if item not in preference_index:
            preference_index[item] = base_max + idx

    ready: List[Any] = [n for n, deg in indegree.items() if deg == 0]
    ready.sort(key=lambda x: preference_index.get(x, 0))

    result: List[Any] = []
    while ready:
        node = ready.pop(0)
        result.append(node)
        for succ in adjacency.get(node, ()):  # type: ignore[arg-type]
            indegree[succ] -= 1
            if indegree[succ] == 0:
                ready.append(succ)
        ready.sort(key=lambda x: preference_index.get(x, 0))

    if len(result) != len(nodes):
        # Cycle detected.
        raise ValueError('Cycle detected in media ordering')
    return result


def _fallback_linear_merger(base_list: Sequence[Any], other_list: Sequence[Any]) -> List[Any]:
    """Simple deterministic fallback merge used when we detect a true cycle.

    This keeps all items in base_list in place, then appends any new items from
    other_list preserving their relative order.
    """
    merged: List[Any] = list(base_list)
    seen: Set[Any] = set(base_list)
    for item in other_list:
        if item not in seen:
            merged.append(item)
            seen.add(item)
    return merged


def _pick_cycle_pair(nodes: Sequence[Any], edges: Iterable[Tuple[Any, Any]]) -> Optional[Tuple[Any, Any]]:
    """Pick a representative conflicting pair from a cyclic graph.

    We do a simple search for an edge that participates in a cycle by
    performing DFS from each edge's source to see if we can reach its target
    again. This is kept small because the number of media files per widget is
    typically low.
    """
    adjacency: Dict[Any, Set[Any]] = defaultdict(set)
    for a, b in edges:
        adjacency[a].add(b)

    def has_path(start: Any, target: Any, limit: int = 50) -> bool:
        # Bounded DFS to avoid pathological graphs.
        stack: List[Any] = [start]
        visited: Set[Any] = set()
        depth: Dict[Any, int] = {start: 0}
        while stack:
            node = stack.pop()
            if node == target and depth[node] > 0:
                return True
            if depth[node] >= limit:
                continue
            if node in visited:
                continue
            visited.add(node)
            for succ in adjacency.get(node, ()):  # type: ignore[arg-type]
                if succ not in depth:
                    depth[succ] = depth[node] + 1
                stack.append(succ)
        return False

    for a, b in edges:
        # If we can reach a from b, then a->b is on a cycle.
        if has_path(b, a):
            return (a, b)
    return None


def _merge_media_lists(
    base_list: Sequence[Any],
    other_list: Sequence[Any],
    seen_warning_paths: Set[Tuple[str, Tuple[Any, Any]]],
    *,
    label: str,
) -> Tuple[List[Any], Set[Tuple[str, Tuple[Any, Any]]]]:
    """Merge two lists of media paths preserving explicit relative order.

    - base_list: list from the already-merged Media.
    - other_list: list from the Media being added.
    - seen_warning_paths: cache of already-warned (label, (a, b)) pairs.
    - label: 'js' or 'css[medium]' used for warning messages.

    The function:
      * Gathers explicit pairwise ordering constraints from each operand
        separately (consecutive pairs only).
      * Runs a stable topological sort over the union of items.
      * If a true cycle in the explicit constraints is detected, it emits a
        MediaOrderConflictWarning once per representative pair and falls back
        to a deterministic linear merge.
    """
    # Nodes: unique items from both lists, preserving first-seen order.
    nodes_ordered: List[Any] = []
    seen_nodes: Set[Any] = set()
    for item in itertools.chain(base_list, other_list):
        if item not in seen_nodes:
            seen_nodes.add(item)
            nodes_ordered.append(item)

    # Edges: explicit constraints from each list separately.
    edges: List[Tuple[Any, Any]] = []
    for seq in (base_list, other_list):
        prev: Optional[Any] = None
        for item in seq:
            if prev is not None and prev != item:
                edges.append((prev, item))
            prev = item

    if not edges or len(nodes_ordered) <= 1:
        # No constraints or trivial.
        return list(nodes_ordered), seen_warning_paths

    try:
        ordered = _stable_topological_sort(nodes_ordered, edges, base_preference=base_list)
        return ordered, seen_warning_paths
    except ValueError:
        # True cycle: pick a representative conflicting pair.
        pair = _pick_cycle_pair(nodes_ordered, edges)
        if pair is not None:
            key = (label, pair)
            if key not in seen_warning_paths:
                seen_warning_paths.add(key)
                a, b = pair
                warnings.warn(
                    MediaOrderConflictWarning(
                        'Detected duplicate Media files in an opposite order:\n%s\n%s' % (a, b)
                    ),
                    stacklevel=3,
                )
        # Fallback linear merge.
        merged = _fallback_linear_merger(base_list, other_list)
        return merged, seen_warning_paths