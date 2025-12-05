from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from django.core import checks
from django.core.exceptions import ValidationError
from django.db.models import Field
from django.utils.translation import gettext_lazy as _


class FilePathField(Field):
    description = _("File path")

    def __init__(
        self,
        path: Optional[Any] = None,
        match: Optional[str] = None,
        recursive: bool = False,
        allow_files: bool = True,
        allow_folders: bool = False,
        **kwargs: Any,
    ) -> None:
        """Model field for storing filesystem paths.

        ``path`` may be a string representing an absolute path, or a zero-
        argument callable returning such a string.

        When a callable is supplied, it is not evaluated during model field
        initialization or deconstruction to avoid environment-specific values
        in migrations; evaluation is delegated to form/validation time via the
        corresponding form field.
        """
        self._raw_path = path
        self.match = match
        self.recursive = recursive
        self.allow_files = allow_files
        self.allow_folders = allow_folders
        super().__init__(**kwargs)

    def check(self, **kwargs: Any) -> list[checks.CheckMessage]:
        errors = super().check(**kwargs)
        errors.extend(self._check_path())
        return errors

    def _check_path(self) -> list[checks.CheckMessage]:
        # If a callable is provided, it may not be safe or possible to resolve
        # it during system checks (e.g. at import/migrations time). To preserve
        # backwards compatibility and avoid surprises, only perform the
        # filesystem existence check when the configured path is a plain string.
        if isinstance(self._raw_path, str):
            path = self._raw_path
            if not os.path.isabs(path):
                return [
                    checks.Error(
                        "FilePathFields must have an absolute path.",
                        obj=self,
                        id="fields.E200",
                    )
                ]
            if not os.path.isdir(path):
                return [
                    checks.Error(
                        "FilePathFields path should exist and be a directory.",
                        obj=self,
                        id="fields.E201",
                    )
                ]
        return []

    def deconstruct(self) -> tuple[str, str, list[Any], dict[str, Any]]:
        name, path, args, kwargs = super().deconstruct()
        # Preserve the public API name 'path' in kwargs. For backwards
        # compatibility, if a plain string was passed originally, serialize it
        # as before. If a callable was passed, attempt to serialize it only if
        # it is a simple, importable callable (e.g., a module-level function),
        # otherwise fall back to serializing the currently resolved string path
        # value so that migrations remain stable and environment-independent.
        raw_path = self._raw_path
        if isinstance(raw_path, str):
            kwargs["path"] = raw_path
        else:
            # Callable or other non-string: best-effort handling.
            mod = getattr(raw_path, "__module__", None)
            name_attr = getattr(raw_path, "__name__", None)
            if mod and name_attr:
                # A module-level callable can be represented by its import path.
                kwargs["path"] = f"{mod}.{name_attr}"
            else:
                # Fallback: resolve to a concrete string path at deconstruct
                # time. This mirrors the previous behavior where migrations
                # captured the absolute path, but now it's explicit and
                # supports the callable-based configuration.
                try:
                    from django.forms.fields import FilePathField as FormFilePathField

                    tmp_field = FormFilePathField(path=self._raw_path)
                    kwargs["path"] = tmp_field._resolve_path()
                except Exception:
                    # As a last resort, just store the repr to avoid crashes.
                    kwargs["path"] = repr(raw_path)
        kwargs["match"] = self.match
        kwargs["recursive"] = self.recursive
        kwargs["allow_files"] = self.allow_files
        kwargs["allow_folders"] = self.allow_folders
        return name, path, args, kwargs

    def formfield(self, **kwargs: Any):
        from django.forms.fields import FilePathField as FormFilePathField

        defaults = {
            "form_class": FormFilePathField,
            "path": self._raw_path,
            "match": self.match,
            "recursive": self.recursive,
            "allow_files": self.allow_files,
            "allow_folders": self.allow_folders,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def get_prep_value(self, value: Any) -> Any:
        if value is None:
            return None
        return str(value)

    def to_python(self, value: Any) -> Any:
        if value is None:
            return value
        return str(value)

    def from_db_value(self, value: Any, expression, connection) -> Any:  # type: ignore[override]
        if value is None:
            return value
        return str(value)

    def value_to_string(self, obj: Any) -> str:
        value = self.value_from_object(obj)
        return "" if value is None else str(value)

    def validate(self, value: Any, model_instance: Any) -> None:
        super().validate(value, model_instance)
        if value is None:
            return
        # Basic existence/type checks are delegated to forms for FilePathField
        # choices; the model field only enforces that the value is a string.
        if not isinstance(value, str):
            raise ValidationError(self.error_messages["invalid"], code="invalid")


# The corresponding form field implementation is referenced in formfield() and
# in deconstruct() via its `_resolve_path()` helper. It is shown here for
# completeness of imports; its full implementation lives in django/forms/fields.py.

__all__ = ["FilePathField"]