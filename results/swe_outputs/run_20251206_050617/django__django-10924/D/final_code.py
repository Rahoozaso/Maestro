from __future__ import annotations

import os
from typing import Any, Optional

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

        ``path`` may be either:

        * a string representing an absolute filesystem path, or
        * a zero-argument callable returning such a string.

        When a callable is supplied, it is not evaluated during model field
        initialization, system checks, or deconstruction, in order to avoid
        capturing environment-specific values (such as machine-local base
        directories) in migrations. Instead, evaluation is delegated to the
        corresponding form field at form/validation time.
        """
        self.path = path
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
        """Run system checks on the configured path.

        For backwards compatibility, when a plain string path is provided this
        method enforces that it is an absolute path to an existing directory.

        When a callable is provided, no filesystem checks are performed at this
        stage, as resolving the callable may depend on environment-specific
        configuration that is not available (or desirable to access) during
        system checks or migration generation.
        """
        if isinstance(self.path, str):
            path = self.path
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
        # Non-string (e.g. callable) paths are not validated here.
        return []

    def deconstruct(self) -> tuple[str, str, list[Any], dict[str, Any]]:
        """Return enough information to recreate this field in migrations.

        To keep migrations stable and environment-independent, the ``path``
        argument is serialized as follows:

        * If ``path`` is a plain string, it is serialized unchanged.
        * If ``path`` is a simple, importable callable (for example, a
          module-level function), it is serialized as that callable object so
          that migrations refer to the callable rather than to any particular
          resolved filesystem path.
        * For other non-string, non-importable values, the value is left as-is
          and delegated to Django's migration serialization logic.
        """
        name, path, args, kwargs = super().deconstruct()

        raw_path = self.path
        if isinstance(raw_path, str):
            kwargs["path"] = raw_path
        else:
            # Best-effort support for callable paths: if the callable has a
            # module and name, it can usually be imported and serialized
            # directly by the migration framework.
            mod = getattr(raw_path, "__module__", None)
            name_attr = getattr(raw_path, "__name__", None)
            if mod and name_attr:
                # Keep the callable itself; migrations will import it.
                kwargs["path"] = raw_path
            else:
                # Fallback: store the raw value and let Django's built-in
                # migration serializer handle (or fail) as appropriate.
                kwargs["path"] = raw_path

        kwargs["match"] = self.match
        kwargs["recursive"] = self.recursive
        kwargs["allow_files"] = self.allow_files
        kwargs["allow_folders"] = self.allow_folders
        return name, path, args, kwargs

    def formfield(self, **kwargs: Any):
        from django.forms.fields import FilePathField as FormFilePathField

        defaults = {
            "form_class": FormFilePathField,
            # Pass the raw "path" through; the form field is responsible for
            # resolving callables at validation/render time.
            "path": self.path,
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


__all__ = ["FilePathField"]