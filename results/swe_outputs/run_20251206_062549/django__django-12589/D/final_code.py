from django.core.exceptions import FieldError
from django.db.models.expressions import Col, Ref
from django.db.models.sql.constants import MULTI
from django.db.models.sql.query import get_order_dir


class SQLCompiler:
    # ... other methods and initializers would be here in the real Django file ...

    def get_group_by(self, select, order_by=None):
        """Return a list of 2-tuples of form (sql, params) for GROUP BY.

        This implementation makes sure that when grouping by annotated
        expressions (for example Subquery-based annotations), the GROUP BY
        clause uses the full SQL expression rather than only a column/alias
        reference. This avoids ambiguous column errors such as
        GROUP BY "status" when multiple joined tables expose a column of the
        same name, while preserving Django's normal behavior for simple
        field/column annotations.
        """
        # If there is no grouping configured on the query, don't emit GROUP BY.
        if not self.query.group_by:
            return []

        # Start from the query's explicit group_by expressions.
        expressions = list(self.query.group_by)

        # Add expressions implied by ORDER BY when necessary.
        if order_by is None:
            order_by = self.query.order_by

        if order_by:
            for expr, (sql, params, is_ref) in order_by:
                if is_ref:
                    # Ensure that any Ref used for ordering and also required
                    # for grouping is considered in the GROUP BY expressions.
                    expressions.append(expr)

        result = []
        seen = set()

        for expr in expressions:
            # Skip duplicates based on a stable identity when available.
            expr_id = getattr(expr, "identity", None) or id(expr)
            if expr_id in seen:
                continue
            seen.add(expr_id)

            compiled = None

            # When the grouping expression is a Ref, it usually points to an
            # annotation or select alias. We want to group by the *underlying*
            # expression only when that annotation is itself an expression
            # (e.g. Subquery, Func, arithmetic, etc.), while preserving the
            # legacy behavior of grouping by the alias for simple Col/field
            # references.
            if isinstance(expr, Ref):
                alias = expr.refs
                source_expression = self.query.annotations.get(alias)

                if source_expression is not None:
                    # If the annotation is just a Col (or wraps a concrete
                    # column without further expression logic), grouping by
                    # the alias is equivalent and keeps behavior consistent
                    # with previous Django versions.
                    if isinstance(source_expression, Col):
                        compiled = self.compile(expr)
                    else:
                        # For more complex expressions (such as Subquery or
                        # other Expression subclasses), group by the full
                        # expression SQL to avoid ambiguous column references.
                        compiled = self.compile(source_expression)
                else:
                    # Fallback to the default behavior: group by the Ref
                    # itself (compiled to its alias/column).
                    compiled = self.compile(expr)
            else:
                compiled = self.compile(expr)

            if isinstance(compiled, tuple):
                sql, params = compiled
            else:
                # Some compilers may return raw SQL strings.
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