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
        # Based on Django 3.0's SQLCompiler.get_group_by implementation,
        # with the critical change that we don't collapse Ref() of
        # annotated expressions to a bare column/alias name. Instead we
        # compile the underlying expression stored on the query.
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
            expr_id = getattr(expr, 'identity', None) or id(expr)
            if expr_id in seen:
                continue
            seen.add(expr_id)

            # When the group_by entry is a Ref (which usually points to an
            # annotation or select alias), try to resolve it back to the
            # underlying expression held by the query so that we group by
            # the full expression instead of just the alias name.
            if isinstance(expr, Ref):
                # expr.refs is the alias it refers to.
                alias = expr.refs
                source_expression = None

                # Look up the annotation by alias name.
                if alias in self.query.annotations:
                    source_expression = self.query.annotations[alias]
                # If not found in annotations, fall back to compiling the Ref
                # itself as per normal behavior.
                if source_expression is not None:
                    compiled = self.compile(source_expression)
                else:
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
        if hasattr(node, 'as_sql'):
            return node.as_sql(self, self.connection)
        raise NotImplementedError('The real SQLCompiler.compile implementation is provided by Django.')