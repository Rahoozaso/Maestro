from django.core.exceptions import FieldError
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import Col, Ref
from django.db.models.options import Options
from django.db.models.sql.constants import (
    INNER,
    LOUTER,
    ORDER_DIR,
)
from django.db.models.sql.datastructures import EmptyResultSet, Join
from django.db.models.sql.where import AND
from django.utils.functional import cached_property


class SQLCompiler:
    def __init__(self, query, connection, using):
        self.query = query
        self.connection = connection
        self.using = using
        self.quote_cache = {}
        self.ordering_parts = connection.ops.ordering_parts_regex

    def get_default_ordering(self):
        ordering = self.query.get_meta().ordering
        if isinstance(ordering, str):
            return (ordering,)
        return ordering

    def _quote_expr(self, expression):
        """Quote an expression (used for raw column / SQL snippets)."""
        return expression

    def _setup_joins(self, name, exclusions=()):
        """Stub for join setup; real implementation is complex."""
        # For the purposes of this simplified module, assume the
        # implementation returns (table, column, None) or (None, None, None).
        raise NotImplementedError

    def _get_order_dir(self, field, default='ASC'):
        """Return the field name and direction for an order specifier."""
        dirn = default
        if field[0] == '-':
            dirn = 'DESC'
            field = field[1:]
        return field, dirn

    def compile(self, node):
        """Compile a node to SQL and params. Placeholder for real impl."""
        raise NotImplementedError

    def get_order_by(self):
        """Returns a list of 3-tuples of (expr, (sql, params), is_ref)."""
        if self.query.extra_order_by:
            ordering = self.query.extra_order_by
        elif not self.query.default_ordering:
            ordering = self.query.order_by
        elif self.query.order_by:
            ordering = self.query.order_by
        else:
            ordering = self.get_default_ordering()

        if not ordering:
            return [], False

        result = []
        seen = set()
        for element in ordering:
            if isinstance(element, (list, tuple)):
                expr, is_ref = element
            else:
                expr, is_ref = element, False

            if isinstance(expr, str):
                # Normal path: a field name or an expression string.
                col, order = self._get_order_dir(expr, 'ASC')
                if (
                    col not in self.query.annotations
                    and col in self.query.annotations_select
                ):
                    # Order by an annotation.
                    annotation = self.query.annotations_select[col]
                    if getattr(annotation, 'contains_aggregate', False):
                        # Refuse to ORDER BY an aggregate that is not in the
                        # SELECT list if not supported by the backend.
                        if not self.connection.features.supports_order_by_all:
                            continue
                    result.append((annotation, (None, []), False))
                    continue
                elif col in self.query.extra_select:
                    # Order by an extra select.
                    result.append((self.query.extra_select[col], (None, []), False))
                    continue
                else:
                    # Order by a column.
                    table, column, _ = self._setup_joins(col, [])
                    if table and column:
                        sql = (
                            self.connection.ops.quote_name(table)
                            + '.'
                            + self.connection.ops.quote_name(column)
                        )
                    else:
                        # Ordering by a non-joinable field (like an alias or a
                        # raw SQL snippet).
                        sql = self._quote_expr(col)

                    # Normalize multiline SQL before applying the
                    # ordering_parts regex so the de-duplication key for ORDER
                    # BY clauses is based on the full expression instead of
                    # just the last line. This fixes incorrect removal of
                    # distinct multiline RawSQL order_by expressions.
                    sql_oneline = ' '.join(sql.splitlines())

                    match = self.ordering_parts.search(sql_oneline)
                    if match:
                        without_ordering = match.group(1)
                    else:
                        without_ordering = sql_oneline

                    if without_ordering in seen:
                        continue
                    seen.add(without_ordering)

                    if order == 'DESC':
                        sql = '%s DESC' % sql
                    else:
                        sql = '%s ASC' % sql

                    result.append((None, (sql, []), False))
            else:
                # expr is already a compiled expression (Annotation, RawSQL,
                # Func, etc.).
                sql, params = self.compile(expr)

                # Normalize multiline SQL before applying the ordering_parts
                # regex so that multiline RawSQL ORDER BY expressions are
                # compared based on their full content instead of a trailing
                # line.
                sql_oneline = ' '.join(sql.splitlines())

                match = self.ordering_parts.search(sql_oneline)
                if match:
                    without_ordering = match.group(1)
                else:
                    without_ordering = sql_oneline

                if without_ordering in seen:
                    continue
                seen.add(without_ordering)

                result.append((expr, (sql, params), True))

        return result, True