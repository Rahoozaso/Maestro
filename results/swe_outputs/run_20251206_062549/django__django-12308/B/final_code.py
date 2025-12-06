from __future__ import annotations

import json

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import formats_html, linebreaksbr
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


def display_for_field(value, field, empty_value_display="-"):
    """Return a display value for a field's value in the admin list/detail views.

    This function is used by the admin when rendering readonly_fields and
    list_display values. It mirrors the normal form/widget rendering behavior
    while staying independent from forms.
    """
    if value is None:
        return empty_value_display

    # Special-case JSONField so that readonly values are rendered as valid JSON
    # rather than Python's dict/list repr. Using the field's prepare_value keeps
    # behavior consistent with Django's form/widget pipeline and allows custom
    # JSONField implementations to control serialization and error handling
    # (e.g. InvalidJSONInput).
    if isinstance(field, models.JSONField):
        try:
            prepared = field.prepare_value(value)
        except ValidationError:
            # Fall back to the empty display in line with other invalid values.
            return empty_value_display

        # prepare_value() for JSONField typically returns a string that's already
        # JSON-encoded. If it's a string, return as-is. If a Python structure is
        # returned for some custom field, serialize it to JSON here.
        if isinstance(prepared, str):
            return prepared
        return json.dumps(prepared)

    # Fallbacks for other field types (simplified canonical implementation).
    if isinstance(field, (models.DateField, models.DateTimeField, models.TimeField)):
        return field.value_to_string(models.Model(), value)

    if isinstance(field, (models.BooleanField, models.NullBooleanField)):
        return _("Yes") if value else _("No")

    if isinstance(field, models.TextField):
        return mark_safe(linebreaksbr(value))

    # Default behavior: use the field's value_to_string or the plain value.
    try:
        return field.value_to_string(models.Model(), value)
    except Exception:
        return formats_html("{}", value)