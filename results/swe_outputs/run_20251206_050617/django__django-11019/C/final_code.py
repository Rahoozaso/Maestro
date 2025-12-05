import itertools
import warnings
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import Promise
from django.utils.html import escape, format_html, html_safe
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


class MediaOrderConflictWarning(UserWarning):
    """Warning raised when media files cannot be consistently ordered.

    This is emitted only when there is a real cycle in the explicit ordering
    constraints between media files, i.e. when it's impossible to determine a
    single order that satisfies all widgets' declared media orderings.
    """

    pass


@html_safe
class Media:
    """Handle media (CSS/JS) definitions on widgets.

    This version refines Django's merge algorithm to base ordering conflicts on
    explicit constraints only. It avoids emitting spurious
    ``MediaOrderConflictWarning`` instances when merging three or more ``Media``
    objects whose individual orderings are compatible.
    """

    def __init__(self, media=None, **kwargs):
        """Initialize a Media instance.

        Args:
            media: Optional existing object with ``css`` and ``js`` attributes
                whose values are used as the initial media definitions.
            **kwargs: Alternative way to provide ``css`` and ``js`` when
                ``media`` isn't supplied.

        Raises:
            TypeError: If unsupported keyword arguments are given or if ``css``
                is of an unexpected type.
        """
        if media is not None:
            css = getattr(media, "css", {})
            js = getattr(media, "js", [])
        else:
            css = kwargs.pop("css", {})
            js = kwargs.pop("js", [])
        if kwargs:
            raise TypeError("Unknown keyword arguments for Media: %s" % list(kwargs))

        # Internal normalized representations.
        self._css: Dict[str, List[Any]] = {}
        self._js: List[Any] = []
        # Cache of pairs we've already warned about to avoid duplicate warnings.
        self._media_conflict_cache: Set[Tuple[str, Tuple[Any, Any]]] = set()

        # Normalize css: mapping medium -> list.
        if isinstance(css, (list, tuple)):
            # Backwards-compatible: css=['base.css'] means 'all'.
            if css:
                self._css["all"] = list(css)
        elif isinstance(css, dict):
            for medium, paths in css.items():
                self._css[medium] = list(paths)
        else:
            raise TypeError("css must be dict or list/tuple")

        # Normalize js: list.
        self._js = list(js)

    @property
    def css(self) -> Dict[str, List[Any]]:
        """Return the CSS media mapping (medium -> list of paths)."""

        return self._css

    @property
    def js(self) -> List[Any]:
        """Return the list of JavaScript media paths."""

        return self._js

    def __str__(self) -> str:
        """Return the rendered HTML representation of this media."""

        return self.render()

    def __bool__(self) -> bool:
        """Return ``True`` if there is at least one CSS or JS file."""

        return bool(self._css or self._js)

    def __add__(self, other: "Media") -> "Media":
        """Merge two ``Media`` instances, preserving declared orderings.

        The merge algorithm:
        * Collects the explicit ordering constraints present within each
          operand independently (i.e. consecutive pairs in a single list).
        * Performs a stable topological sort over the union of all media
          files based solely on those explicit constraints.
        * If and only if the constraints contain a true cycle, emits a single
          ``MediaOrderConflictWarning`` per representative conflicting pair and
          falls back to a deterministic linear merge that preserves the order
          of the left operand and appends new items from the right.
        """

        if not isinstance(other, Media):
            return NotImplemented

        merged_media = Media()
        # Copy current normalized structures.
        merged_media._css = {}
        merged_media._js = []

        # Merge conflict caches so we don't warn repeatedly for same pair.
        combined_conflict_cache: Set[Tuple[str, Tuple[Any, Any]]] = set()
        combined_conflict_cache.update(getattr(self, "_media_conflict_cache", set()))
        combined_conflict_cache.update(getattr(other, "_media_conflict_cache", set()))

        # Merge JS.
        merged_js, combined_conflict_cache = _merge_media_lists(
            self._js,
            other._js,
            combined_conflict_cache,
            label="js",
        )
        merged_media._js = merged_js

        # Merge CSS per medium.
        merged_css: Dict[str, List[Any]] = {}
        all_media_types = set(self._css.keys()) | set(other._css.keys())
        for medium in all_media_types:
            base_list_for_medium = self._css.get(medium, [])
            other_list_for_medium = other._css.get(medium, [])
            merged_for_medium, combined_conflict_cache = _merge_media_lists(
                base_list_for_medium,
                other_list_for_medium,
                combined_conflict_cache,
                label=f"css[{medium}]",
            )
            if merged_for_medium:
                merged_css[medium] = merged_for_medium
        merged_media._css = merged_css

        merged_media._media_conflict_cache = combined_conflict_cache
        return merged_media

    def __radd__(self, other: "Media") -> "Media":
        """Support ``sum()`` with ``Media()`` as the start value."""

        if other == 0:
            return self
        if not isinstance(other, Media):
            return NotImplemented
        return other.__add__(self)

    def render(self) -> str:
        """Render all media as a single HTML string containing tags."""

        return "\n".join(itertools.chain(self.render_css(), self.render_js()))

    def render_js(self) -> List[str]:
        """Render JavaScript media as a list of ``<script>`` tag strings."""

        return [
            format_html("<script src=\"{}\"></script>", escape(path))
            for path in self._js
        ]

    def render_css(self) -> List[str]:
        """Render CSS media as a list of ``<link>`` tag strings."""

        rendered_lines: List[str] = []
        for medium, paths in self._css.items():
            for path in paths:
                if medium:
                    rendered_lines.append(
                        format_html(
                            '<link href="{}" type="text/css" media="{}" rel="stylesheet">',
                            escape(path),
                            escape(medium),
                        )
                    )
                else:
                    rendered_lines.append(
                        format_html(
                            '<link href="{}" type="text/css" rel="stylesheet">',
                            escape(path),
                        )
                    )
        return rendered_lines


def _stable_topological_sort(
    nodes: Sequence[Any],
    edges: Iterable[Tuple[Any, Any]],
    base_preference: Sequence[Any],
) -> List[Any]:
    """Return a stable topological ordering for the given nodes.

    Args:
        nodes: Sequence of unique items.
        edges: Iterable of ``(a, b)`` pairs expressing a strict ordering
            constraint ``a < b``.
        base_preference: Sequence whose order is preferred among all valid
            topological orders.

    Raises:
        ValueError: If a cycle is detected.
    """

    adjacency: Dict[Any, Set[Any]] = defaultdict(set)
    indegree: Dict[Any, int] = {node: 0 for node in nodes}

    for source, target in edges:
        if source == target:
            continue
        if target not in indegree or source not in indegree:
            # Ignore constraints that mention unknown nodes.
            continue
        if target not in adjacency[source]:
            adjacency[source].add(target)
            indegree[target] += 1

    # Compute preference indices: items earlier in ``base_preference`` win,
    # falling back to the original ``nodes`` order.
    preference_index: Dict[Any, int] = {}
    for index, item in enumerate(base_preference):
        if item not in preference_index:
            preference_index[item] = index
    base_max_index = len(base_preference)
    for index, item in enumerate(nodes):
        if item not in preference_index:
            preference_index[item] = base_max_index + index

    ready: List[Any] = [node for node, degree in indegree.items() if degree == 0]
    ready.sort(key=lambda item: preference_index.get(item, 0))

    ordered_nodes: List[Any] = []
    while ready:
        node = ready.pop(0)
        ordered_nodes.append(node)
        for successor in adjacency.get(node, ()):  # type: ignore[arg-type]
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
        ready.sort(key=lambda item: preference_index.get(item, 0))

    if len(ordered_nodes) != len(nodes):
        # Cycle detected.
        raise ValueError("Cycle detected in media ordering")
    return ordered_nodes


def _fallback_linear_merger(base_list: Sequence[Any], other_list: Sequence[Any]) -> List[Any]:
    """Fallback merge used when a true cycle is detected.

    This keeps all items from ``base_list`` in place, then appends any new
    items from ``other_list`` while preserving their relative order.
    """

    merged_items: List[Any] = list(base_list)
    seen_items: Set[Any] = set(base_list)
    for item in other_list:
        if item not in seen_items:
            merged_items.append(item)
            seen_items.add(item)
    return merged_items


def _pick_cycle_pair(
    nodes: Sequence[Any], edges: Iterable[Tuple[Any, Any]]
) -> Optional[Tuple[Any, Any]]:
    """Select a representative conflicting edge from a cyclic constraint graph.

    The function searches for an edge that participates in a cycle by running a
    bounded depth-first search from each edge's target back to its source.

    Args:
        nodes: Sequence of nodes involved in the constraints (unused but kept
            for future extensibility).
        edges: Iterable of directed edges ``(a, b)``.

    Returns:
        A tuple ``(a, b)`` representing a conflicting edge, or ``None`` if no
        such edge is found.
    """

    adjacency: Dict[Any, Set[Any]] = defaultdict(set)
    for source, target in edges:
        adjacency[source].add(target)

    def has_path(start: Any, target: Any, limit: int = 50) -> bool:
        """Return True if there is a path from ``start`` to ``target``.

        The search depth is bounded by ``limit`` to guard against pathologically
        large graphs. Media lists are usually small, so this is sufficient.
        """

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
            for successor in adjacency.get(node, ()):  # type: ignore[arg-type]
                if successor not in depth:
                    depth[successor] = depth[node] + 1
                stack.append(successor)
        return False

    for source, target in edges:
        # If we can reach ``source`` from ``target``, then ``source -> target``
        # is part of a cycle.
        if has_path(target, source):
            return (source, target)
    return None


def _merge_media_lists(
    base_list: Sequence[Any],
    other_list: Sequence[Any],
    seen_warning_paths: Set[Tuple[str, Tuple[Any, Any]]],
    *,
    label: str,
) -> Tuple[List[Any], Set[Tuple[str, Tuple[Any, Any]]]]:
    """Merge two sequences of media paths, preserving explicit relative order.

    The algorithm works as follows:

    * Consider only *explicit* constraints expressed within each list
      separately, i.e. for each consecutive pair ``(x, y)`` in a list we add a
      constraint ``x < y``.
    * Build a graph from the union of all constraints and run a stable
      topological sort, using ``base_list`` as the primary ordering preference.
    * If the constraints contain a true cycle, choose a representative
      conflicting pair, emit a ``MediaOrderConflictWarning`` (once per pair per
      ``label``), and fall back to a simple deterministic linear merge.

    This approach prevents spurious ``MediaOrderConflictWarning`` emissions
    that arose from inferring additional constraints across separate media
    objects, while still detecting genuine ordering cycles.

    Args:
        base_list: Sequence from the already-merged ``Media`` instance.
        other_list: Sequence from the ``Media`` instance being added.
        seen_warning_paths: Cache of already-warned ``(label, (a, b))`` pairs.
        label: A string such as ``'js'`` or ``'css[all]'`` used in warnings.

    Returns:
        A tuple ``(merged_list, updated_seen_warning_paths)``.
    """

    # Nodes: unique items from both lists, preserving first-seen order.
    nodes_ordered: List[Any] = []
    seen_nodes: Set[Any] = set()
    for item in itertools.chain(base_list, other_list):
        if item not in seen_nodes:
            seen_nodes.add(item)
            nodes_ordered.append(item)

    # Edges: explicit constraints from each list separately (consecutive pairs).
    edges: List[Tuple[Any, Any]] = []
    for sequence in (base_list, other_list):
        previous_item: Optional[Any] = None
        for item in sequence:
            if previous_item is not None and previous_item != item:
                edges.append((previous_item, item))
            previous_item = item

    if not edges or len(nodes_ordered) <= 1:
        # No constraints or trivial case: just return items in first-seen order.
        return list(nodes_ordered), seen_warning_paths

    try:
        ordered_nodes = _stable_topological_sort(
            nodes_ordered,
            edges,
            base_preference=base_list,
        )
        return ordered_nodes, seen_warning_paths
    except ValueError:
        # True cycle: pick a representative conflicting pair and warn once.
        conflicting_pair = _pick_cycle_pair(nodes_ordered, edges)
        if conflicting_pair is not None:
            warning_key = (label, conflicting_pair)
            if warning_key not in seen_warning_paths:
                seen_warning_paths.add(warning_key)
                first, second = conflicting_pair
                warnings.warn(
                    MediaOrderConflictWarning(
                        "Detected duplicate Media files in an opposite order:\n%s\n%s"
                        % (first, second)
                    ),
                    stacklevel=3,
                )
        # Fallback linear merge.
        merged = _fallback_linear_merger(base_list, other_list)
        return merged, seen_warning_paths