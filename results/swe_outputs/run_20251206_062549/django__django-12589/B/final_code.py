from django.core.exceptions import FieldError
from django.db.models.expressions import Col, Ref
from django.db.models.sql.constants import MULTI
from django.db.models.sql.query import get_order_dir


class SQLCompiler:
    # ... other methods and initializers would be here in the real Django file ...

    def get_group_by(self, select, order_by=None):
        """Return a list of 2-tuples of form (sql, params) for GROUP BY.

        This implementation follows Django 2.2-style semantics and ensures that
        when grouping by annotated expressions (e.g. Subquery-based
        annotations referenced via Ref()), the GROUP BY clause uses the full
        SQL expression rather than a bare column/alias reference. This
        prevents errors such as PostgreSQL's "column reference \"status\" is
        ambiguous" when joined tables expose columns with the same name.
        """
        if self.query.group_by is None:
            # Default: group by all non-aggregate select columns.
            if self.query.annotation_select and not self.query.values_select:
                group_by = [
                    (sel, None)
                    for sel in select
                    if not getattr(sel, 'is_summary', False)
                ]
            else:
                group_by = []
        elif self.query.group_by is True:
            # True means: group by the select list (non aggregates).
            group_by = [
                (sel, None)
                for sel in select
                if not getattr(sel, 'is_summary', False)
            ]
        else:
            # Explicit group_by expressions.
            group_by = list(self.query.group_by)

        if order_by is None:
            order_by = self.query.order_by

        # Normalize group_by to a list of expressions (strip potential tuples
        # that may include ordering direction or other metadata).
        expressions = []
        for element in group_by:
            if isinstance(element, tuple):
                expr, _ = element
            else:
                expr = element
            expressions.append(expr)

        # Add expressions from ORDER BY that should also participate in GROUP BY
        # (non-aggregated, non-constant entries).
        if order_by:
            for order_expr, (sql, params, is_ref) in order_by:
                resolved, _ = get_order_dir(order_expr, 'ASC')
                if getattr(resolved, 'is_summary', False):
                    continue
                expressions.append(resolved)

        result = []
        seen = set()

        for expr in expressions:
            # Skip identical expressions based on identity, falling back to id.
            expr_id = getattr(expr, 'identity', None) or id(expr)
            if expr_id in seen:
                continue
            seen.add(expr_id)

            # If the group_by entry is a Ref pointing to an annotation, resolve
            # to the underlying annotation expression so that GROUP BY uses the
            # full SQL expression rather than the alias/column name.
            if isinstance(expr, Ref):
                alias = expr.refs
                source_expression = None

                # Look up the annotation by alias name.
                if alias in self.query.annotations:
                    source_expression = self.query.annotations[alias]

                if source_expression is not None:
                    compiled = self.compile(source_expression)
                else:
                    # Fall back to compiling the Ref itself.
                    compiled = self.compile(expr)

            elif isinstance(expr, Col):
                # Standard column reference; compile normally.
                compiled = self.compile(expr)

            else:
                # Arbitrary expression; compile directly.
                compiled = self.compile(expr)

            # The compiler normally returns (sql, params) for expressions, but
            # handle the case of raw SQL strings defensively.
            if isinstance(compiled, tuple):
                sql, params = compiled
            else:
                sql, params = compiled, []

            # Skip aggregates and window expressions in GROUP BY.
            if getattr(expr, 'is_summary', False):
                continue
            if getattr(expr, 'contains_aggregate', False):
                continue
            if getattr(expr, 'contains_over_clause', False):
                continue

            result.append((sql, params))

        # When there are multiple tables involved (MULTI) and DISTINCT ON is
        # used, some backends require DISTINCT fields to appear in GROUP BY as
        # well. Ensure that those fields, resolved as full expressions, are
        # also included without collapsing them to bare column names.
        if (
            self.query.combinator is None and
            self.query.distinct and
            self.query.distinct_fields
        ):
            distinct_expressions = []
            for field in self.query.distinct_fields:
                if field in self.query.annotations:
                    distinct_expressions.append(self.query.annotations[field])
                else:
                    # Fallback to model field column for non-annotated DISTINCT
                    # fields; this mirrors how Django resolves DISTINCT ON.
                    col = self.query.model._meta.get_field(field).get_col(
                        self.query.get_initial_alias()
                    )
                    distinct_expressions.append(col)

            for expr in distinct_expressions:
                expr_id = getattr(expr, 'identity', None) or id(expr)
                if expr_id in seen:
                    continue
                seen.add(expr_id)
                compiled = self.compile(expr)
                if isinstance(compiled, tuple):
                    sql, params = compiled
                else:
                    sql, params = compiled, []
                result.append((sql, params))

        return result

    # Placeholder compile implementation for completeness in this standalone
    # snippet. In Django, this method is fully implemented and much richer.
    def compile(self, node, select_format=False):
        """Compile an expression node into SQL and parameters.

        This stub exists only so this file is syntactically complete in
        isolation. In the real Django codebase, SQLCompiler.compile is
        provided by django.db.models.sql.compiler and knows how to handle
        Expression objects, Col, Ref, Subquery, etc.
        """
        if hasattr(node, 'as_sql'):
            return node.as_sql(self, self.connection)
        raise NotImplementedError('The real SQLCompiler.compile implementation is provided by Django.')