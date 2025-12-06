from django.core.exceptions import FieldError
from django.db.models.expressions import Col, Ref
from django.db.models.sql.constants import MULTI
from django.db.models.sql.query import get_order_dir


class SQLCompiler:
    """Minimal stand-in for Django's SQLCompiler focusing on get_group_by.

    This version is tailored to address the regression where GROUP BY
    would use a bare alias like "status" for a Subquery-based annotation
    instead of the full SQL expression, which can cause ambiguous column
    errors in databases such as PostgreSQL.
    """

    def get_group_by(self, select, order_by=None):
        """Return a list of 2-tuples of form (sql, params) for GROUP BY.

        This implementation mirrors Django 2.2/3.0 behavior but ensures that
        Ref() objects that point at annotations (for example Subquery-based
        annotations) are expanded to the underlying expression when used in
        GROUP BY. That forces SQL like::

            GROUP BY (SELECT ...)

        instead of::

            GROUP BY "status"

        which avoids "column reference is ambiguous" errors when joins
        introduce other columns with the same name.
        """
        if not self.query.group_by:
            return []

        expressions = list(self.query.group_by)
        if order_by is None:
            order_by = self.query.order_by

        # Add any ordering expressions that need to be included in GROUP BY.
        if order_by:
            for expr, (sql, params, is_ref) in order_by:
                if is_ref:
                    expressions.append(expr)

        result = []
        seen = set()

        for expr in expressions:
            # Avoid processing the same expression multiple times.
            expr_id = getattr(expr, "identity", None) or id(expr)
            if expr_id in seen:
                continue
            seen.add(expr_id)

            # If the group_by entry is a Ref to an annotation, group by the
            # underlying expression instead of the simple alias/column.
            if isinstance(expr, Ref):
                alias = expr.refs
                source_expression = None

                if alias in self.query.annotations:
                    source_expression = self.query.annotations[alias]

                if source_expression is not None:
                    compiled = self.compile(source_expression)
                else:
                    compiled = self.compile(expr)
            else:
                compiled = self.compile(expr)

            if isinstance(compiled, tuple):
                sql, params = compiled
            else:
                sql, params = compiled, []

            result.append((sql, params))

        return result

    def compile(self, node, select_format=False):
        """Compile an expression node into SQL and parameters.

        In the real Django codebase, this method is fully featured and lives
        on django.db.models.sql.compiler.SQLCompiler. Here it's only present
        so the module is syntactically complete.
        """
        if hasattr(node, "as_sql"):
            return node.as_sql(self, self.connection)
        raise NotImplementedError(
            "The real SQLCompiler.compile implementation is provided by Django."
        )