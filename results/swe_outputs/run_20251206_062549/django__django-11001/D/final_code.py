import collections
import functools
import hashlib
import json
import operator
import warnings
from collections import namedtuple
from itertools import chain

from django.core.exceptions import EmptyResultSet, FieldError
from django.db import DEFAULT_DB_ALIAS, NotSupportedError, connections
from django.db.models.aggregates import Count
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import ColPairs, F, Ref, Value
from django.db.models.functions import Cast
from django.db.models.lookups import Exact, In
from django.db.models.query_utils import Q
from django.db.models.sql.constants import (
    CURSOR,
    FOR_UPDATE,
    GET_ITERATOR_CHUNK_SIZE,
    NO_RESULTS,
    ORDER_DIR,
)
from django.db.models.sql.datastructures import Empty
from django.db.models.sql.where import AND, OR, NothingNode, WhereNode
from django.utils.functional import cached_property
from django.utils.hashable import make_hashable
from django.utils.inspect import func_supports_parameter
from django.utils.itercompat import is_iterable
from django.utils.regex_helper import _lazy_re_compile


class SQLCompiler:
    def __init__(self, query, connection, using):
        self.query = query.clone()
        self.connection = connection
        self.using = using
        self.quote_cache = {}
        self.col_aliases = {}
        self.ordering_parts = _lazy_re_compile("(.*) (ASC|DESC)")

    def quote_name_unless_alias(self, name):
        if name in self.quote_cache:
            return self.quote_cache[name]
        r = self.connection.ops.quote_name(name)
        self.quote_cache[name] = r
        return r

    def _order_by_pairs(self):
        # Placeholder implementation. In the real Django codebase this
        # would yield (expr, (sql, params, is_ref)) for each ORDER BY item.
        for order_by in self.query.order_by or []:
            if hasattr(order_by, 'as_sql'):
                sql, params = order_by.as_sql(self, self.connection)
            else:
                sql, params = str(order_by), []
            yield order_by, (sql, params, False)

    def get_order_by(self):
        """Return SQL and parameters for the ORDER BY clause.

        This method is responsible for building the ORDER BY portion of the query
        and for removing duplicate ordering expressions. Historically, duplicate
        detection was done by feeding the full SQL fragment to the
        ``ordering_parts`` regex and storing only the matched substring in a
        ``seen`` set. When ``sql`` contained newlines (e.g. multiline RawSQL
        expressions), the regex could end up matching only the final line of the
        expression. If multiple different expressions had an identical trailing
        line, later ones were incorrectly treated as duplicates and dropped.

        To avoid this, normalize the SQL to a single-line representation before
        applying ``ordering_parts.search`` for duplicate detection. This keeps
        the semantics of the generated SQL while making comparisons robust to
        newlines inside expressions.
        """
        result = []
        seen = set()

        # _order_by_pairs is assumed to yield (expression, (sql, params, is_ref))
        for expr, (sql, params, is_ref) in self._order_by_pairs():
            if not sql:
                continue

            # Normalize newlines and extraneous whitespace for the purpose of
            # duplicate detection. ``splitlines()`` handles "\n", "\r\n", and "\r".
            normalized_sql = " ".join(sql.splitlines())

            if self.ordering_parts is not None:
                match = self.ordering_parts.search(normalized_sql)
                if match:
                    without_ordering = match.group(1)
                else:
                    # Fallback: use the normalized SQL fragment as-is.
                    without_ordering = normalized_sql
            else:
                # If no regex is defined, use the normalized SQL directly.
                without_ordering = normalized_sql

            if without_ordering in seen:
                continue
            seen.add(without_ordering)

            # Preserve the original SQL and params in the final ORDER BY list.
            result.append((sql, params, is_ref))

        return result

    # The rest of SQLCompiler's methods would be here in the real Django source.