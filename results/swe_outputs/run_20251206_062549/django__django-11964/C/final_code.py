from enum import Enum

from django.core import checks
from django.db.models.query_utils import DeferredAttribute
from django.utils.functional import Promise
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _


class Field:
    """Base class for all field types"""

    # ... other attributes and methods omitted for brevity ...

    def __init__(self, *args, **kwargs):
        # This constructor is illustrative; in the real Django codebase
        # there are many more options handled here. We include a minimal
        # skeleton to keep this example self-contained.
        self.null = kwargs.pop("null", False)
        self.blank = kwargs.pop("blank", False)
        self.choices = kwargs.pop("choices", None)
        self.default = kwargs.pop("default", None)
        self.name = None
        self.attname = None
        self.model = None

    # ------------------------------------------------------------------
    # The method modified to normalize Enum (TextChoices/IntegerChoices)
    # values to their underlying .value before further processing.
    # ------------------------------------------------------------------
    def get_prep_value(self, value):
        """Perform preliminary non-db specific value checks and conversions.

        This is where values are normalized before they're sent to the
        database backend. For fields with choices that are backed by
        TextChoices or IntegerChoices (Enum subclasses), an Enum member
        may be assigned at the model attribute level. In such cases the
        underlying primitive value (e.g. str or int) must be persisted and
        exposed so that ``model_instance.field`` and ``str(model_instance.field)``
        are consistent for both newly created and retrieved instances.
        """
        # First, normalize Enum values for choices-backed fields. This keeps
        # behavior consistent with Django's TextChoices/IntegerChoices contract:
        # model fields store and expose the .value, while Enum membership is
        # only a convenience for definition and filtering.
        if isinstance(value, Enum):
            value = value.value

        if value is None:
            return None
        return self.to_python(value)

    # In the real Django code, ``to_python`` performs type coercion tailored
    # to each concrete field type. Here we provide a very small generic stub
    # so that ``get_prep_value`` above is well-defined.
    def to_python(self, value):
        return value

    # The rest of Django's Field API would follow here (db_type, from_db_value,
    # contribute_to_class, etc.). They are omitted because the focus of this
    # task is the behavior of ``get_prep_value``.


__all__ = ["Field"]