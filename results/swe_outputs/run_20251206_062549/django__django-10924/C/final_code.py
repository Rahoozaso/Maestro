from django.core import checks
from django.db.models import Field
from django.utils import six
from django.utils.module_loading import import_string


class FilePathField(Field):
    description = "A file path"

    def __init__(self, verbose_name=None, name=None, path='', match=None,
                 recursive=False, allow_files=True, allow_folders=False, **kwargs):
        """FilePathField optionally takes a filesystem path or a callable.

        `path` may be either a string (existing behavior) or a zero-argument
        callable returning a string path. At runtime, ``self.path`` exposes the
        resolved path (calling the callable when necessary), while migrations
        preserve the original callable reference instead of the evaluated path
        (handled in :meth:`deconstruct`).
        """
        # Store the original argument (string or callable) separately so that
        # ``deconstruct()`` can see the unevaluated value.
        self._path = path
        super(FilePathField, self).__init__(verbose_name, name, **kwargs)
        self.match = match
        self.recursive = recursive
        self.allow_files = allow_files
        self.allow_folders = allow_folders

    @property
    def path(self):
        """Return the effective path for this field.

        If the original ``path`` argument was a callable, call it (without
        arguments) to obtain the actual filesystem path. If it was a string,
        return it unchanged. This keeps the rest of ``FilePathField``'s logic
        unaware of whether a callable was used.
        """
        value = self._path
        if callable(value):
            value = value()
        return value

    @path.setter
    def path(self, value):
        """Allow runtime mutation of ``field.path`` for backwards-compatibility."""
        self._path = value

    def check(self, **kwargs):
        errors = super(FilePathField, self).check(**kwargs)
        errors.extend(self._check_path())
        return errors

    def _check_path(self):
        # Use the original stored value; we only need to know that *something*
        # was provided, not its resolved value.
        if not self._path:
            return [
                checks.Error(
                    "FilePathFields must have a 'path' argument.",
                    obj=self,
                    id='fields.E100',
                )
            ]
        return []

    def deconstruct(self):
        """Deconstruct the field for migrations, preserving callable ``path``.

        When ``path`` is a string, preserve existing behavior (serialize the
        string value). When ``path`` is a callable, serialize a reference to
        the callable (e.g., ``'myapp.utils.local_file_dir'``) instead of the
        evaluated absolute path, so the migration is not environment-specific.
        """
        name, path, args, kwargs = super(FilePathField, self).deconstruct()

        # Existing behavior for auxiliary arguments
        if self.match is not None:
            kwargs['match'] = self.match
        if self.recursive:
            kwargs['recursive'] = self.recursive
        if not self.allow_files:
            kwargs['allow_files'] = self.allow_files
        if self.allow_folders:
            kwargs['allow_folders'] = self.allow_folders

        original_path = self._path

        if callable(original_path):
            # If it's already a string, assume it's an import path the user
            # passed explicitly and reuse it.
            if isinstance(original_path, six.string_types):
                kwargs['path'] = original_path
            else:
                # Serialize a dotted import path to the callable when possible.
                mod = getattr(original_path, '__module__', None)
                qualname = getattr(original_path, '__qualname__', None)
                if mod and qualname:
                    kwargs['path'] = '%s.%s' % (mod, qualname)
                else:
                    # Fallback: store the callable as-is. This mirrors Django's
                    # behavior for unserializable callables and will surface an
                    # error during migration serialization if inappropriate.
                    kwargs['path'] = original_path
        else:
            # String path: preserve existing behavior
            if original_path:
                kwargs['path'] = original_path

        return name, path, args, kwargs

    def get_internal_type(self):
        return 'FilePathField'

    def to_python(self, value):
        if isinstance(value, six.text_type) or value is None:
            return value
        return six.text_type(value)

    def get_prep_value(self, value):
        value = super(FilePathField, self).get_prep_value(value)
        if value is None:
            return None
        return six.text_type(value)

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        return six.text_type(value)