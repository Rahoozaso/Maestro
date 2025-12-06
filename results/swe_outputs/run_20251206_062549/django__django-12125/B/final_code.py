import collections.abc
import datetime
import decimal
import functools
import math
import uuid
from enum import Enum
from functools import singledispatch
from types import BuiltinFunctionType, BuiltinMethodType, FunctionType, MethodType
from typing import Any

from django.db.migrations.utils import resolve_callable
from django.utils.functional import LazyObject


def class_to_dotted_path(cls: type) -> str:
    """Return the dotted path used for migration serialization of a class.

    This respects nested/inner classes by using ``__qualname__`` instead of
    just ``__name__``, so that e.g. Outer.Inner becomes
    'path.to.models.Outer.Inner' instead of incorrectly 'path.to.models.Inner'.
    """
    module = cls.__module__
    # __qualname__ includes nesting (e.g. 'Outer.Inner'). It is the most
    # reliable way to preserve the relationship between outer and inner
    # classes for serialization.
    qualname = getattr(cls, "__qualname__", cls.__name__)
    return f"{module}.{qualname}"


class BaseSerializer:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        """Return a 2-tuple: (string, {imports or settings})."""
        raise NotImplementedError("Subclasses must implement serialize().")


class Serializer(BaseSerializer):
    @classmethod
    def serialize(cls, value):
        return serializer_factory(value).serialize()


class BaseSequenceSerializer(BaseSerializer):
    def _format(self):
        raise NotImplementedError

    def serialize(self):
        strings = []
        imports = set()
        format_ = self._format()
        for item in self.value:
            string, item_imports = serializer_factory(item).serialize()
            strings.append(string)
            imports.update(item_imports)
        return format_.format(", ".join(strings)), imports


class ListSerializer(BaseSequenceSerializer):
    def _format(self):
        return "[{}]"


class TupleSerializer(BaseSequenceSerializer):
    def _format(self):
        # A single value in a tuple is not a tuple.
        if len(self.value) == 1:
            return "({},)"
        return "({})"


class SetSerializer(BaseSequenceSerializer):
    def _format(self):
        if not self.value:
            return "set()"
        return "{{{}}}"


class DictSerializer(BaseSerializer):
    def serialize(self):
        strings = []
        imports = set()
        for key, value in self.value.items():
            key_string, key_imports = serializer_factory(key).serialize()
            value_string, value_imports = serializer_factory(value).serialize()
            strings.append(f"{key_string}: {value_string}")
            imports.update(key_imports)
            imports.update(value_imports)
        return "{" + ", ".join(strings) + "}", imports


class SetTypeSerializer(BaseSerializer):
    def serialize(self):
        return "set", {"import": "set"}


class FrozensetSerializer(BaseSequenceSerializer):
    def _format(self):
        if not self.value:
            return "frozenset()"
        return "frozenset({{{}}})"


class FrozensetTypeSerializer(BaseSerializer):
    def serialize(self):
        return "frozenset", {"import": "frozenset"}


class UUIDSerializer(BaseSerializer):
    def serialize(self):
        return f"uuid.UUID('{self.value}')", {"import": "uuid"}


class DecimalSerializer(BaseSerializer):
    def serialize(self):
        return f"decimal.Decimal('{self.value}')", {"import": "decimal"}


class DatetimeSerializer(BaseSerializer):
    def serialize(self):
        return repr(self.value), {"import": "datetime"}


class DateSerializer(BaseSerializer):
    def serialize(self):
        return repr(self.value), {"import": "datetime"}


class TimeSerializer(BaseSerializer):
    def serialize(self):
        return repr(self.value), {"import": "datetime"}


class TimedeltaSerializer(BaseSerializer):
    def serialize(self):
        return repr(self.value), {"import": "datetime"}


class SimpleLazyObjectSerializer(BaseSerializer):
    def serialize(self):
        # The unwrapped value is serialized.
        value = self.value._wrapped
        return serializer_factory(value).serialize()


class DeconstructableSerializer(BaseSerializer):
    def serialize(self):
        name, path, args, kwargs = self.value.deconstruct()
        imports = {"import": path}
        arg_strings = []
        for arg in args:
            arg_string, arg_imports = serializer_factory(arg).serialize()
            arg_strings.append(arg_string)
            imports.update(arg_imports)
        kwarg_strings = []
        for kwarg_name, kwarg_value in sorted(kwargs.items()):
            kwarg_string, kwarg_imports = serializer_factory(kwarg_value).serialize()
            kwarg_strings.append(f"{kwarg_name}={kwarg_string}")
            imports.update(kwarg_imports)
        return (
            f"{path}({', '.join(arg_strings + kwarg_strings)})",
            imports,
        )


class FunctionTypeSerializer(BaseSerializer):
    def serialize(self):
        # Use class_to_dotted_path-like behavior for functions, but since this
        # is a function, not a class, we manually compose the path.
        module = self.value.__module__
        qualname = getattr(self.value, "__qualname__", self.value.__name__)
        full_path = f"{module}.{qualname}"
        return full_path, {"import": full_path}


class MethodTypeSerializer(BaseSerializer):
    def serialize(self):
        func = self.value.__func__
        module = func.__module__
        qualname = getattr(func, "__qualname__", func.__name__)
        full_path = f"{module}.{qualname}"
        return full_path, {"import": full_path}


class FloatSerializer(BaseSerializer):
    def serialize(self):
        if math.isinf(self.value):
            if self.value > 0:
                return "float('inf')", {"import": "builtins.float"}
            else:
                return "float('-inf')", {"import": "builtins.float"}
        if math.isnan(self.value):
            return "float('nan')", {"import": "builtins.float"}
        return repr(self.value), set()


class BytesSerializer(BaseSerializer):
    def serialize(self):
        return repr(self.value), set()


class EnumSerializer(BaseSerializer):
    """Serializer for Enum-like classes/instances.

    Ensures that nested enums like Thing.State are serialized as
    'app.models.Thing.State' instead of 'app.models.State'.
    """

    def serialize(self):
        enum_class = self.value.__class__
        dotted = class_to_dotted_path(enum_class)
        return f"{dotted}.{self.value.name}", {"import": dotted}


class ClassSerializer(BaseSerializer):
    def serialize(self):
        value = self.value
        # Use the helper to construct the full dotted path, including outer
        # classes when serializing nested classes.
        dotted = class_to_dotted_path(value)
        return dotted, {"import": dotted}


@singledispatch
def serializer_factory(value: Any) -> BaseSerializer:  # pragma: no cover - default
    if isinstance(value, LazyObject):
        value = resolve_callable(value)
    if isinstance(value, list):
        return ListSerializer(value)
    if isinstance(value, tuple):
        return TupleSerializer(value)
    if isinstance(value, set):
        return SetSerializer(value)
    if isinstance(value, frozenset):
        return FrozensetSerializer(value)
    if isinstance(value, dict):
        return DictSerializer(value)
    if isinstance(value, uuid.UUID):
        return UUIDSerializer(value)
    if isinstance(value, decimal.Decimal):
        return DecimalSerializer(value)
    if isinstance(value, datetime.datetime):
        return DatetimeSerializer(value)
    if isinstance(value, datetime.date):
        return DateSerializer(value)
    if isinstance(value, datetime.time):
        return TimeSerializer(value)
    if isinstance(value, datetime.timedelta):
        return TimedeltaSerializer(value)
    if isinstance(value, type(set())):
        return SetTypeSerializer(value)
    if isinstance(value, type(frozenset())):
        return FrozensetTypeSerializer(value)
    if isinstance(value, type):
        return ClassSerializer(value)
    if isinstance(value, Enum):
        return EnumSerializer(value)
    if isinstance(value, (FunctionType, BuiltinFunctionType)):
        return FunctionTypeSerializer(value)
    if isinstance(value, (MethodType, BuiltinMethodType)):
        return MethodTypeSerializer(value)
    if isinstance(value, float):
        return FloatSerializer(value)
    if isinstance(value, bytes):
        return BytesSerializer(value)
    if hasattr(value, "deconstruct"):
        return DeconstructableSerializer(value)
    return BaseSerializer(value)


# Register serializers for specific collection ABCs to ensure subclasses
# of these types are correctly handled.
serializer_factory.register(list, lambda v: ListSerializer(v))
serializer_factory.register(tuple, lambda v: TupleSerializer(v))
serializer_factory.register(set, lambda v: SetSerializer(v))
serializer_factory.register(frozenset, lambda v: FrozensetSerializer(v))
serializer_factory.register(dict, lambda v: DictSerializer(v))
serializer_factory.register(collections.abc.Mapping, lambda v: DictSerializer(v))
serializer_factory.register(collections.abc.Sequence, lambda v: ListSerializer(v))
serializer_factory.register(collections.abc.Set, lambda v: SetSerializer(v))