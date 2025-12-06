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
        callable returning a string path. In both cases the resolved absolute path
        is used at runtime, but migrations will preserve the callable reference
        rather than the evaluated path (handled in deconstruct()).
        """
        self._path = path  # May be a string or a callable; do not eagerly resolve
        # For backward compatibility, retain the public attribute name `path`.
        # When `path` is a callable, expose the resolved value via a property
        # rather than storing the evaluated value here.
        super(FilePathField, self).__init__(verbose_name, name, **kwargs)
        self.match = match
        self.recursive = recursive
        self.allow_files = allow_files
        self.allow_folders = allow_folders

    @property
    def path(self):
        """Return the effective path for this field.

        If the original `path` argument was a callable, call it (without
        arguments) to obtain the actual filesystem path. If it was a string,
        return it unchanged. This keeps the rest of FilePathField's logic
        unaware of whether a callable was used.
        """
        value = self._path
        if callable(value):
            value = value()
        return value

    @path.setter
    def path(self, value):
        # Maintain a setter for compatibility with any existing code that
        # mutates `field.path` directly.
        self._path = value

    def check(self, **kwargs):
        errors = super(FilePathField, self).check(**kwargs)
        errors.extend(self._check_path())
        return errors

    def _check_path(self):
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
        """Deconstruct the field for migrations, preserving callable `path`.

        When `path` is a string, preserve existing behavior (serialize the string
        value). When `path` is a callable, serialize a reference to the callable
        (e.g., 'myapp.utils.local_file_dir') instead of the evaluated absolute
        path, so the migration is not environment-specific.
        """
        name, path, args, kwargs = super(FilePathField, self).deconstruct()

        # Preserve all existing kwargs first (match, recursive, allow_files, etc.)
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
            # For a callable, serialize a dotted path reference instead of
            # evaluating it. This follows the common Django pattern for
            # serializing callables (e.g., validators).
            mod = getattr(original_path, '__module__', None)
            qualname = getattr(original_path, '__qualname__', None)
            if mod and qualname:
                kwargs['path'] = "%s.%s" % (mod, qualname)
            else:
                # Fallback: store the callable as-is; this mirrors Django's
                # behavior for certain unserializable callables and will raise
                # during migration serialization if inappropriate.
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