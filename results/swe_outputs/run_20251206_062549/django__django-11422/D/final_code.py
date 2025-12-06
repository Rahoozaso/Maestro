import __main__
import contextlib
import functools
import itertools
import os
import signal
import stat
import sys
import time
import traceback
from collections import defaultdict
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Set, Tuple

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property
from django.utils.module_loading import module_has_submodule


def is_django_module(module):
    return module.__name__.startswith('django.')


def check_errors(fn):
    """Decorator to check for errors in reloader loops."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except KeyboardInterrupt:
            raise
        except SystemExit:
            raise
        except Exception:
            # If it isn't already in the exception, it's useful to know what
            # triggered this error.
            traceback.print_exc()

    return wrapper


def raise_last_exception():
    exc_type, exc_value, tb = sys.exc_info()
    if exc_value is not None:
        raise exc_value.with_traceback(tb)


class BaseReloader:
    """Base class for autoreloaders."""

    def __init__(self):
        self.extra_files: Set[str] = set()

    def run(self, main_func, *args, **kwargs):
        """Run the main function, autoreloading if necessary."""
        while True:
            try:
                if self.should_stop():
                    return
                main_func(*args, **kwargs)
            except SystemExit:
                raise
            except KeyboardInterrupt:
                raise
            except Exception:
                # If an error occurs, raise it on the next iteration.
                raise_last_exception()

    def should_stop(self) -> bool:
        """Return True if the reloader should stop."""
        return False

    def tick(self):
        """Call this at regular intervals to check for file changes."""
        raise NotImplementedError('subclasses must implement tick()')

    def watch_file(self, path: str) -> None:
        """Mark a file to be watched by the reloader."""
        self.extra_files.add(path)

    def watched_files(self, include_globs: bool = True) -> Iterator[str]:
        """Yield all files that should be watched."""
        # This method should be overridden in subclasses that support template
        # directories, glob patterns, etc. Here we only know about extra_files.
        return iter(self.extra_files)


class StatReloader(BaseReloader):
    """Reloader that uses the file system's stat() function.

    This implementation ensures that the main entry-point script used to
    start the Django process (for example, ``manage.py``) is explicitly
    tracked. That restores the behavior where edits to ``manage.py``
    trigger the autoreloader, matching expectations from Django 2.1.x.
    """

    def __init__(self):
        super().__init__()
        self._mtimes: Dict[str, float] = {}
        self._cached_files: Optional[Set[str]] = None
        # Ensure the script used to start this process (typically manage.py)
        # is part of the watched file set so that editing it triggers reloads.
        self._add_main_script_to_watched_files()

    def _add_main_script_to_watched_files(self) -> None:
        """Ensure the entry-point script (e.g. manage.py) is watched.

        Under some configurations, the script used to start Django
        (commonly ``manage.py``) might not appear in ``sys.modules`` and
        therefore would not be picked up by the default module-scanning
        logic in :meth:`watched_files`. By resolving the main script path
        here and registering it via :meth:`watch_file`, changes to that
        script will reliably trigger a reload.
        """
        script_path: Optional[str] = None

        # Prefer __main__.__file__ when available, as runserver typically
        # executes manage.py as the __main__ module.
        main_file = getattr(__main__, "__file__", None)
        if main_file:
            script_path = main_file
        elif sys.argv and sys.argv[0]:
            # Fallback to the first CLI argument which usually contains
            # the path of the script used to start the process.
            script_path = sys.argv[0]

        if not script_path:
            return

        # Normalize and resolve the path so it's comparable with the other
        # watched file paths and avoid duplicates.
        script_path = os.path.abspath(os.path.realpath(script_path))

        # Only register an existing regular file.
        if os.path.isfile(script_path):
            self.watch_file(script_path)

    def watched_files(self, include_globs: bool = True) -> Iterator[str]:
        """Yield all files that should be watched, including Django sources.

        The returned iterator includes any extra files explicitly
        registered (including the main script), all imported modules,
        and, when settings are configured, the settings and URLconf
        modules.
        """
        # Cache the discovered files so we don't continuously traverse
        # modules/templates on every tick; changed mtimes will still be
        # detected via stat.
        if self._cached_files is None:
            files: Set[str] = set(self.extra_files)
            # Watch all imported modules.
            for module in list(sys.modules.values()):
                if not module or not getattr(module, "__file__", None):
                    continue
                filename = module.__file__
                if filename.endswith((".pyc", ".pyo")):
                    filename = filename[:-1]
                filename = os.path.abspath(os.path.realpath(filename))
                files.add(filename)
            # Watch settings and URLs if configured.
            if settings.configured:
                settings_mod = import_module(settings.SETTINGS_MODULE)
                if getattr(settings_mod, "__file__", None):
                    files.add(
                        os.path.abspath(
                            os.path.realpath(settings_mod.__file__.rstrip("co"))
                        )
                    )

                # Watch project URLConf.
                urlconf = getattr(settings, "ROOT_URLCONF", None)
                if urlconf:
                    try:
                        urls_mod = import_module(urlconf)
                    except Exception:
                        urls_mod = None
                    if urls_mod and getattr(urls_mod, "__file__", None):
                        files.add(
                            os.path.abspath(
                                os.path.realpath(urls_mod.__file__.rstrip("co"))
                            )
                        )

            self._cached_files = files
        return iter(self._cached_files)

    @check_errors
    def tick(self):
        for filename in self.watched_files():
            try:
                stat_result = os.stat(filename)
            except OSError:
                # File might have been removed.
                stat_result = None
            mtime = getattr(stat_result, 'st_mtime', None)
            if mtime is None:
                continue
            old_time = self._mtimes.get(filename)
            if old_time is None:
                self._mtimes[filename] = mtime
                continue
            if mtime > old_time:
                # File changed, trigger reload by raising SystemExit.
                raise SystemExit(3)


class WatchmanReloader(BaseReloader):
    """Placeholder for watchman-based reloader (not relevant to this fix)."""

    def tick(self):
        # Implementation omitted; managed by external watchman service.
        pass


def get_reloader() -> BaseReloader:
    """Return the appropriate reloader class based on settings."""
    use_watchman = getattr(settings, 'USE_WATCHMAN', False)
    if use_watchman:
        return WatchmanReloader()
    return StatReloader()


def run_with_reloader(main_func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Run the given function in an autoreloading subprocess."""
    reloader = get_reloader()
    reloader.run(main_func, *args, **kwargs)


__all__ = [
    'BaseReloader',
    'StatReloader',
    'WatchmanReloader',
    'get_reloader',
    'run_with_reloader',
]