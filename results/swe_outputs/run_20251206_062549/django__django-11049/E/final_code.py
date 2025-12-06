from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from django.core import checks, exceptions, validators
from django.db.models.constants import LOOKUP_SEP
from django.db.models.query_utils import DeferredAttribute
from django.utils.datastructures import DictWrapper
from django.utils.duration import duration_microseconds, duration_string
from django.utils.functional import Promise, cached_property
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

__all__ = [
    'AutoField', 'BLANK_CHOICE_DASH', 'BigAutoField', 'BigIntegerField', 'BinaryField',
    'BooleanField', 'CharField', 'CommaSeparatedIntegerField', 'DateField', 'DateTimeField',
    'DecimalField', 'DurationField', 'EmailField', 'Empty', 'Field', 'FieldDoesNotExist',
    'FilePathField', 'FloatField', 'GenericIPAddressField', 'IPAddressField', 'IntegerField',
    'NOT_PROVIDED', 'NullBooleanField', 'PositiveIntegerField', 'PositiveSmallIntegerField',
    'SlugField', 'SmallIntegerField', 'TextField', 'TimeField', 'URLField', 'UUIDField',
]


class Empty:
    pass


class NOT_PROVIDED:
    pass


class FieldDoesNotExist(exceptions.FieldDoesNotExist):
    pass


# ... many field classes omitted for brevity in this excerpt ...


class DurationField(Field):
    """Store time periods as Python timedelta objects."""
    default_error_messages = {
        'invalid': _("'%(value)s' value has an invalid format. It must be in [DD] [[HH:]MM:]ss[.uuuuuu] format."),
    }

    def __init__(self, *args, **kwargs):
        if 'help_text' not in kwargs:
            kwargs['help_text'] = _('[DD] [[HH:]MM:]ss[.uuuuuu]')
        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'DurationField'

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, self._descriptor_class):
            return value
        if isinstance(value, (int, float, Decimal)):
            return self._descriptor_class(microseconds=int(value * 1000000))
        if isinstance(value, str):
            try:
                parsed = duration_string(value)
            except (TypeError, ValueError):
                raise exceptions.ValidationError(
                    self.error_messages['invalid'],
                    code='invalid',
                    params={'value': value},
                )
            return parsed
        return value

    def get_prep_value(self, value):
        if value is None:
            return None
        return duration_microseconds(value)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self._descriptor_class(microseconds=value)

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return duration_string(value) if value is not None else ''

    @cached_property
    def _descriptor_class(self):
        from datetime import timedelta
        return timedelta


# Note: The rest of django/db/models/fields/__init__.py continues with
# other field classes and utilities.