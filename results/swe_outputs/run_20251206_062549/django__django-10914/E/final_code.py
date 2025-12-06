import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, Optional, Tuple

from django.core.exceptions import SuspiciousFileOperation
from django.core.files import locks, File
from django.core.files.base import ContentFile
from django.core.files.move import file_move_safe
from django.core.files.storage import Storage
from django.utils._os import safe_join
from django.utils.encoding import filepath_to_uri
from django.utils.functional import LazyObject
from django.utils.timezone import now


class FileSystemStorage(Storage):
    """Standard filesystem storage"""

    def __init__(self, location=None, base_url=None, file_permissions_mode=None,
                 directory_permissions_mode=None):
        self._location = location
        self._base_url = base_url
        self._file_permissions_mode = file_permissions_mode
        self._directory_permissions_mode = directory_permissions_mode

    @property
    def location(self):
        if self._location is None:
            from django.conf import settings
            self._location = settings.MEDIA_ROOT
        return self._location

    @property
    def base_url(self):
        if self._base_url is None:
            from django.conf import settings
            self._base_url = settings.MEDIA_URL
        return self._base_url

    @property
    def file_permissions_mode(self):
        if self._file_permissions_mode is None:
            from django.conf import settings
            # Default file permissions for uploaded files, if not None.
            # If set, Django will set these permissions (via os.chmod) after saving an
            # uploaded file to FileSystemStorage, regardless of whether the upload
            # originated from MemoryUploadedFile or TemporaryUploadedFile.
            self._file_permissions_mode = getattr(settings, 'FILE_UPLOAD_PERMISSIONS', 0o644)
        return self._file_permissions_mode

    @property
    def directory_permissions_mode(self):
        if self._directory_permissions_mode is None:
            from django.conf import settings
            self._directory_permissions_mode = getattr(settings, 'FILE_UPLOAD_DIRECTORY_PERMISSIONS', None)
        return self._directory_permissions_mode

    def _value_or_setting(self, value, setting_name):
        if value is not None:
            return value
        from django.conf import settings
        return getattr(settings, setting_name)

    def _open(self, name, mode='rb'):
        return File(open(self.path(name), mode))

    def _save(self, name, content):
        full_path = self.path(name)

        # Create any intermediate directories that do not exist.
        directory = os.path.dirname(full_path)
        if directory and not os.path.exists(directory):
            try:
                if self.directory_permissions_mode is not None:
                    # Set the umask because os.makedirs() doesn't apply the
                    # "mode" argument to intermediate-level directories.
                    old_umask = os.umask(0)
                    try:
                        os.makedirs(directory, self.directory_permissions_mode)
                    finally:
                        os.umask(old_umask)
                else:
                    os.makedirs(directory)
            except FileExistsError:
                # There's a race between os.path.exists() and os.makedirs(). If
                # os.makedirs() fails with FileExistsError, the directory
                # already exists.
                pass

        # There's a potential race condition between get_available_name and
        # saving the file; it's possible that two threads might return the
        # same name, at which point all sorts of fun happens. So we need to
        # roll our own file open/save logic, including creating the directory
        # if it doesn't exist.

        if hasattr(content, 'temporary_file_path'):
            file_move_safe(content.temporary_file_path(), full_path)
            content.close()
        else:
            # This file has no file path, so we save it the hard way.
            temp_location = full_path + '.tmp'
            with open(temp_location, 'wb+') as temp_file:
                for chunk in content.chunks():
                    temp_file.write(chunk)
            file_move_safe(temp_location, full_path)

        # Apply FILE_UPLOAD_PERMISSIONS (file_permissions_mode) if set.
        perms = self.file_permissions_mode
        if perms is not None:
            try:
                os.chmod(full_path, perms)
            except OSError:
                # Silently ignore chmod errors to avoid breaking uploads on
                # filesystems that do not support chmod or when permissions
                # cannot be changed.
                pass

        return name

    def delete(self, name):
        name = self.path(name)
        if os.path.exists(name):
            os.remove(name)

    def exists(self, name):
        return os.path.exists(self.path(name))

    def listdir(self, path):
        path = self.path(path)
        directories, files = [], []
        for entry in os.scandir(path):
            if entry.is_dir():
                directories.append(entry.name)
            else:
                files.append(entry.name)
        return directories, files

    def path(self, name):
        try:
            path = safe_join(self.location, name)
        except SuspiciousFileOperation:
            raise ValueError("The joined path ({}) is located outside of the base path component ({}).".format(name, self.location))
        return path

    def size(self, name):
        return os.path.getsize(self.path(name))

    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        return filepath_to_uri(os.path.join(self.base_url, name))

    def accessed_time(self, name):
        return self._datetime_from_timestamp(os.path.getatime(self.path(name)))

    def created_time(self, name):
        return self._datetime_from_timestamp(os.path.getctime(self.path(name)))

    def modified_time(self, name):
        return self._datetime_from_timestamp(os.path.getmtime(self.path(name)))

    def _datetime_from_timestamp(self, ts):
        return now().fromtimestamp(ts)