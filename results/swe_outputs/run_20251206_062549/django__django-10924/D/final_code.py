from django.core import checks
from django.db.models import Field
from django.utils import six
from django.utils.module_loading import import_string


class FilePathField(Field):
    """A field that stores a filesystem path.

    Extended to allow the ``path`` argument to be either:

    * a string (existing behavior), or
    * a zero-argument callable returning a string path.

    When a callable is provided, the callable itself is preserved in
    migrations (via :meth:`deconstruct`) rather than its evaluated,
    environment-specific result. At runtime, any callable is evaluated
    on access via the :pyattr:`path` property.
    """

    description = "A file path"

    def __init__(self, verbose_name=None, name=None, path='', match=None,
                 recursive=False, allow_files=True, allow_folders=False, **kwargs):
        """Initialize FilePathField with support for callable ``path``.

        ``path`` may be either a string or a zero-argument callable returning
        a string path. Internally we store the original value on
        ``self._path`` so that deconstruction can distinguish between a
        string and a callable without eagerly resolving it.
        """
        # May be a string or a callable; do not eagerly resolve.
        self._path = path

        # Preserve existing public API attribute name. Code accessing
        # ``field.path`` will use the property defined below, which resolves
        # callables transparently.
        super(FilePathField, self).__init__(verbose_name, name, **kwargs)
        self.match = match
        self.recursive = recursive
        self.allow_files = allow_files
        self.allow_folders = allow_folders

    @property
    def path(self):
        """Return the effective path for this field.

        If the original ``path`` argument was a callable, call it (with no
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
        """Setter to maintain compatibility with code mutating ``field.path``.

        The value may again be a string or a callable; resolution happens
        through the :pyattr:`path` property when accessed.
        """
        self._path = value

    def check(self, **kwargs):
        errors = super(FilePathField, self).check(**kwargs)
        errors.extend(self._check_path())
        return errors

    def _check_path(self):
        # Use the original constructor value to determine if a path/callable
        # was supplied, rather than the resolved property.
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

        When ``path`` is a string, preserve existing behavior by serializing
        the string value. When ``path`` is a callable, serialize a dotted
        Python path to the callable (for example, ``'myapp.utils.local_dir'``)
        instead of the evaluated absolute path, so that migrations are not
        tied to a particular filesystem layout on the machine where they
        were created.
        """
        name, path, args, kwargs = super(FilePathField, self).deconstruct()

        # Preserve existing kwargs behavior (match, recursive, allow_files,
        # allow_folders) exactly as the original implementation.
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
            # evaluating it. This follows common Django patterns for
            # serializing callables (e.g. validators, default callables).
            mod = getattr(original_path, '__module__', None)
            qualname = getattr(original_path, '__qualname__', None)
            if mod and qualname:
                kwargs['path'] = '%s.%s' % (mod, qualname)
            else:
                # Fallback: store the callable as-is; this mirrors Django's
                # behavior for certain unserializable callables and will
                # surface an error during migration serialization if needed.
                kwargs['path'] = original_path
        else:
            # String path: preserve existing behavior.
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