import copy
import datetime
import decimal
import uuid
from enum import Enum

from django.apps import apps
from django.conf import settings
from django.core import checks, exceptions, validators
from django.db import NOT_PROVIDED
from django.db.models.constants import LOOKUP_SEP, OnConflict
from django.db.models.expressions import Col, Expression, ExpressionList, Value
from django.db.models.lookups import Exact
from django.db.models.query_utils import DeferredAttribute
from django.utils import timezone
from django.utils.dateparse import parse_duration
from django.utils.functional import Promise
from django.utils.itercompat import is_iterable
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

__all__ = [
    "AutoField",
    "BLANK_CHOICE_DASH",
    "BigAutoField",
    "BigIntegerField",
    "BinaryField",
    "BooleanField",
    "CharField",
    "CommaSeparatedIntegerField",
    "DateField",
    "DateTimeField",
    "DecimalField",
    "DurationField",
    "EmailField",
    "Empty",
    "Field",
    "FieldDoesNotExist",
    "FilePathField",
    "FloatField",
    "GenericIPAddressField",
    "IPAddressField",
    "IntegerField",
    "NOT_PROVIDED",
    "NullBooleanField",
    "PositiveBigIntegerField",
    "PositiveIntegerField",
    "PositiveSmallIntegerField",
    "SlugField",
    "SmallAutoField",
    "SmallIntegerField",
    "TextField",
    "TimeField",
    "UUIDField",
]


class Empty:
    pass


class FieldDoesNotExist(exceptions.FieldDoesNotExist):
    """The requested model field does not exist"""


class CheckFieldDefaultMixin:
    _default_hint = ("<valid default>", "")

    def _check_default(self):
        if self.has_default() and self.default is not None and not callable(
            self.default
        ):
            return [
                checks.Warning(
                    "Fixed default value provided.",
                    hint=(
                        "It is recommended to use a callable (e.g. a function) "
                        "instead of a fixed value for the default.\n"
                    ),
                    obj=self,
                    id="fields.W161",
                )
            ]
        return []

    def _check_default_callable(self):
        if self.has_default() and callable(self.default):
            try:
                default = self._get_default()
            except Exception:
                return [
                    checks.Error(
                        "The default value of '%s' could not be evaluated." % self.name,
                        hint=self._default_hint[1],
                        obj=self,
                        id="fields.E005",
                    )
                ]
            else:
                return self._check_default_value(default)
        return []

    def _check_default_value(self, default):
        return []


class Field(CheckFieldDefaultMixin):
    """Base class for all field types"""

    empty_strings_allowed = True
    empty_values = list(validators.EMPTY_VALUES)
    default_error_messages = {"invalid_choice": "Value %(value)r is not a valid choice."}
    system_check_deprecated_details = None
    system_check_removed_details = None
    __class_getitem__ = classmethod(type(list[int]).__class_getitem__)

    def __init__(
        self,
        verbose_name=None,
        name=None,
        primary_key=False,
        max_length=None,
        unique=False,
        blank=False,
        null=False,
        db_index=False,
        rel=None,
        default=NOT_PROVIDED,
        editable=True,
        serialize=True,
        unique_for_date=None,
        unique_for_month=None,
        unique_for_year=None,
        choices=None,
        help_text="",
        db_column=None,
        db_tablespace=None,
        auto_created=False,
        validators=(),
        error_messages=None,
        db_comment=None,
        on_update=None,
        db_default=NOT_PROVIDED,
    ):
        self.name = name
        self.verbose_name = verbose_name
        self._verbose_name = None
        self.primary_key = primary_key
        self.max_length = max_length
        self.unique = unique
        self.blank = blank
        self.null = null
        self.remote_field = rel
        self.is_relation = self.remote_field is not None
        self.default = default
        self.editable = editable
        self.serialize = serialize
        self.unique_for_date = unique_for_date
        self.unique_for_month = unique_for_month
        self.unique_for_year = unique_for_year
        self._choices = None
        self.choices = choices
        self.help_text = help_text
        self.db_column = db_column
        self.db_tablespace = db_tablespace or settings.DEFAULT_TABLESPACE
        self.auto_created = auto_created
        self.validators = list(validators)
        self.error_messages = self.error_messages.copy()
        if error_messages is not None:
            self.error_messages.update(error_messages)
        self.db_comment = db_comment
        self._on_update = on_update
        self._on_update_validation_error = None
        self.db_default = db_default
        self._get_default_cached = not callable(default) and default is not NOT_PROVIDED
        self._default = default

        if self.choices is not None and not is_iterable(self.choices):
            raise TypeError("Choices must be an iterable (e.g. a list or tuple).")

        self.db_index = db_index

    @property
    def description(self):
        return "Field"

    @property
    def model(self):
        return getattr(self, "_model", None)

    @model.setter
    def model(self, model):
        self._model = model

    @property
    def attname(self):
        return self.name

    @property
    def concrete(self):
        return not self.is_relation

    def __str__(self):
        if getattr(self, "model", None):
            model = self.model.__name__
        else:
            model = "?"
        return "%s.%s" % (model, self.name)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self)

    def check(self, **kwargs):
        return (
            self._check_field_name()
            + self._check_choices()
            + self._check_db_index()
            + self._check_default()
            + self._check_default_callable()
        )

    def _check_field_name(self):
        if self.name is None:
            return (
                [
                    checks.Error(
                        "Field defines a relation with model '%s', "
                        "which is either not installed, or is abstract." % self.remote_field.model,
                        hint="Ensure that you did not swap a concrete model with an abstract one.",
                        obj=self,
                        id="fields.E300",
                    )
                ]
                if self.remote_field and self.remote_field.model
                else []
            )
        return []

    def _check_choices(self):
        if self.choices is None:
            return []

        if not is_iterable(self.choices) or isinstance(self.choices, str):
            return [
                checks.Error(
                    "'choices' must be an iterable (e.g. a list or tuple).",
                    obj=self,
                    id="fields.E004",
                )
            ]
        return []

    def _check_db_index(self):
        if self.db_index not in (True, False):
            return [
                checks.Error(
                    "'db_index' must be either True or False.",
                    obj=self,
                    id="fields.E007",
                )
            ]
        return []

    @property
    def choices(self):
        return self._choices

    @choices.setter
    def choices(self, value):
        self._choices = value

    def has_default(self):
        return self.default is not NOT_PROVIDED

    def _get_default(self):
        if self._get_default_cached:
            return self._default
        if self.default is NOT_PROVIDED:
            return None
        if callable(self.default):
            return self.default()
        return self.default

    def get_default(self):
        return self._get_default()

    def get_db_prep_save(self, value, connection):
        return self.get_prep_value(value)

    def get_prep_value(self, value):
        return value

    def deconstruct(self):
        """Return enough information to recreate the field as a 4-tuple:

        * The name of the field on the model ("name").
        * The import path of the Field subclass, including the class ("path").
        * Positional arguments ("args").
        * Keyword arguments ("kwargs").

        This is used by the migration framework to serialize fields.
        """
        name = self.name
        path = "%s.%s" % (self.__class__.__module__, self.__class__.__qualname__)
        args = []
        kwargs = {}

        if self.verbose_name is not None:
            kwargs["verbose_name"] = self.verbose_name
        if self.primary_key is True:
            kwargs["primary_key"] = self.primary_key
        if self.max_length is not None:
            kwargs["max_length"] = self.max_length
        if self.unique is not False:
            kwargs["unique"] = self.unique
        if self.blank is not False:
            kwargs["blank"] = self.blank
        if self.null is not False:
            kwargs["null"] = self.null
        if self.db_index is not False:
            kwargs["db_index"] = self.db_index
        if self.default is not NOT_PROVIDED:
            default = self.default
            # For Enum instances, store the enum member itself so that the
            # migrations writer can serialize it by name. This avoids
            # embedding the (potentially translated or otherwise unstable)
            # value and fixes cases where translated values break
            # deserialization, e.g. Status('Good') no longer existing after
            # translation, while Status['GOOD'] remains valid.
            if isinstance(default, Enum):
                kwargs["default"] = default
            else:
                kwargs["default"] = default
        if self.editable is not True:
            kwargs["editable"] = self.editable
        if self.serialize is not True:
            kwargs["serialize"] = self.serialize
        if self.unique_for_date is not None:
            kwargs["unique_for_date"] = self.unique_for_date
        if self.unique_for_month is not None:
            kwargs["unique_for_month"] = self.unique_for_month
        if self.unique_for_year is not None:
            kwargs["unique_for_year"] = self.unique_for_year
        if self.choices is not None:
            kwargs["choices"] = self.choices
        if self.help_text != "":
            kwargs["help_text"] = self.help_text
        if self.db_column is not None:
            kwargs["db_column"] = self.db_column
        if self.db_tablespace != settings.DEFAULT_TABLESPACE:
            kwargs["db_tablespace"] = self.db_tablespace
        if self.auto_created is not False:
            kwargs["auto_created"] = self.auto_created
        if self.validators:
            kwargs["validators"] = self.validators
        if self.error_messages != self.__class__.error_messages:
            kwargs["error_messages"] = self.error_messages
        if self.db_comment is not None:
            kwargs["db_comment"] = self.db_comment
        if self._on_update is not None:
            kwargs["on_update"] = self._on_update
        if self.db_default is not NOT_PROVIDED:
            kwargs["db_default"] = self.db_default
        return name, path, args, kwargs


class CharField(Field):
    description = _("String (up to %(max_length)s)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        if value is None:
            return None
        return str(value)


BLANK_CHOICE_DASH = [("", "---------")]


class IntegerField(Field):
    description = _("Integer")

    def get_prep_value(self, value):
        if value is None:
            return None
        return int(value)


class AutoField(IntegerField):
    pass


class BigIntegerField(IntegerField):
    description = _("Big (8 byte) integer")


class SmallIntegerField(IntegerField):
    description = _("Small integer")


class PositiveIntegerField(IntegerField):
    description = _("Positive integer")


class PositiveSmallIntegerField(SmallIntegerField):
    description = _("Positive small integer")


class BigAutoField(AutoField):
    description = _("Big (8 byte) integer")


class SmallAutoField(AutoField):
    description = _("Small integer")


class TextField(Field):
    description = _("Text")


class BinaryField(Field):
    description = _("Raw binary data")


class BooleanField(Field):
    description = _("Boolean (Either True or False)")


class NullBooleanField(BooleanField):
    description = _("Boolean (Either True, False or None)")


class DateField(Field):
    description = _("Date (without time)")


class TimeField(Field):
    description = _("Time")


class DateTimeField(Field):
    description = _("Date (with time)")


class DurationField(Field):
    description = _("Duration")


class FloatField(Field):
    description = _("Floating point number")


class DecimalField(Field):
    description = _("Decimal number")


class EmailField(CharField):
    description = _("Email address")


class FilePathField(Field):
    description = _("File path")


class SlugField(CharField):
    description = _("Slug (up to %(max_length)s)")


class URLField(CharField):
    description = _("URL")


class GenericIPAddressField(Field):
    description = _("IPv4 or IPv6 address")


class IPAddressField(Field):
    description = _("IPv4 address")


class UUIDField(Field):
    description = _("Universally unique identifier")