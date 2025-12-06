from django.core.exceptions import FieldError
from django.db.models.expressions import Col, Ref
from django.db.models.sql.constants import MULTI
from django.db.models.sql.query import get_order_dir


class SQLCompiler:
    # ... other methods and initializers would be here in the real Django file ...

    def get_group_by(self, select, order_by=None):
        """Return a list of 2-tuples of form (sql, params) for GROUP BY.

        This implementation ensures that when grouping by annotated
        expressions (for example Subquery-based annotations), the
        GROUP BY clause uses the full SQL expression rather than a
        bare column/alias reference. This avoids ambiguous column
        errors such as GROUP BY "status" when multiple joined tables
        expose a column of the same name.
        """
        if not self.query.group_by:
            return []

        expressions = list(self.query.group_by)
        if order_by is None:
            order_by = self.query.order_by

        # Add expressions from the ORDER BY clause if needed.
        if order_by:
            for expr, (sql, params, is_ref) in order_by:
                if is_ref:
                    # For Ref objects in ORDER BY that also need to appear
                    # in GROUP BY, extend expressions list. The underlying
                    # expression will be resolved later when compiling.
                    expressions.append(expr)

        result = []
        seen = set()

        for expr in expressions:
            # Skip identical expressions.
            expr_id = getattr(expr, "identity", None) or id(expr)
            if expr_id in seen:
                continue
            seen.add(expr_id)

            compiled = None

            # When the group_by entry is a Ref (which usually points to an
            # annotation or select alias), try to resolve it back to the
            # underlying expression held by the query so that we group by
            # the full expression instead of just the alias name.
            if isinstance(expr, Ref):
                alias = expr.refs
                source_expression = None

                # First, try to resolve against annotations. This is the
                # common case for annotated Subquery, F, or other
                # expression-based fields that should be grouped by their
                # underlying SQL expression.
                if alias in getattr(self.query, "annotations", {}):
                    source_expression = self.query.annotations[alias]

                # As a fallback, look for a matching column in the select
                # list. This preserves existing behavior when the alias
                # corresponds to a simple column selected from a table.
                if source_expression is None:
                    for sel in select:
                        if isinstance(sel, Col) and sel.alias == alias:
                            source_expression = sel
                            break

                if source_expression is not None:
                    compiled = self.compile(source_expression)
                else:
                    # If we can't resolve a more precise expression, fall
                    # back to compiling the Ref itself.
                    compiled = self.compile(expr)
            else:
                compiled = self.compile(expr)

            if isinstance(compiled, tuple):
                sql, params = compiled
            else:
                # Some compilers might return raw SQL.
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
        if hasattr(node, "as_sql"):
            return node.as_sql(self, self.connection)
        raise NotImplementedError("The real SQLCompiler.compile implementation is provided by Django.")