from __future__ import annotations

from typing import Any, Optional, Iterable, Union, Tuple, Dict, List, Set

from django.core import checks
from django.core.exceptions import FieldError, ImproperlyConfigured
from django.db.models import ForeignObject, ForeignObjectRel, Model
from django.db.models.enums import Choices
from django.db.models.fields import Field
from django.db.models.fields.mixins import FieldCacheMixin
from django.db.models.query_utils import PathInfo
from django.utils.functional import cached_property
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _


class RelatedField(FieldCacheMixin, Field):
    # ... existing implementation of RelatedField ...
    # This placeholder comment indicates omitted, unchanged code.
    pass


class ManyToManyRel(ForeignObjectRel):
    # ... existing implementation of ManyToManyRel ...
    pass


class ManyToManyField(RelatedField):
    """Many-to-many relationship."""

    many_to_many = True
    many_to_one = False
    one_to_many = False
    one_to_one = False

    rel_class = ManyToManyRel

    # ... many existing attributes and methods of ManyToManyField are
    # assumed to be here and are left unchanged.

    def _check_relationship_model(self) -> List[checks.CheckMessage]:
        """Checks that the relationship model is valid."""
        errors: List[checks.CheckMessage] = []

        if self.remote_field.through not in self.model._meta.apps.get_models(include_auto_created=True):
            return errors

        seen_related_fields: List[Field] = []
        for field in self.remote_field.through._meta.fields:
            rel = getattr(field, "remote_field", None)
            if getattr(rel, "model", None) in {self.model, self.remote_field.model}:
                seen_related_fields.append(field)

        if len(seen_related_fields) > 2 and not self.remote_field.through_fields:
            errors.append(
                checks.Error(
                    "The model '%s' has more than one ForeignKey to '%s'." % (
                        self.remote_field.through._meta.label,
                        self.model._meta.label,
                    ),
                    hint=(
                        'If you want to create a recursive relationship, '
                        'use ManyToManyField("%s", through="%s").'
                    ),
                    obj=self,
                    id='fields.E333',
                )
            )
        return errors

    # ... rest of ManyToManyField class and other related code remain unchanged ...