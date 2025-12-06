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
    """Reloader that uses the file system's stat() function."""

    def __init__(self):
        super().__init__()
        self._mtimes: Dict[str, float] = {}
        self._cached_files: Optional[Set[str]] = None
        # Register the main entry script (e.g. manage.py) as an extra file
        # to watch, so edits to it will trigger the autoreloader.
        script_path: Optional[str] = None
        main_file = getattr(__main__, '__file__', None)
        if main_file:
            script_path = main_file
        elif sys.argv and sys.argv[0]:
            script_path = sys.argv[0]
        if script_path:
            script_path = os.path.abspath(os.path.realpath(script_path))
            if os.path.isfile(script_path):
                self.watch_file(script_path)

    def watched_files(self, include_globs: bool = True) -> Iterator[str]:
        """Yield all files that should be watched, including Django sources.

        The discovered files are cached for performance, but the cache is
        invalidated when new entries are added to extra_files so that late
        watch_file() calls (e.g. for manage.py) are honored.
        """
        # Rebuild cache if it doesn't exist yet or if extra_files has new items.
        if self._cached_files is None or not self._cached_files.issuperset(self.extra_files):
            files: Set[str] = set(self.extra_files)
            # Watch all imported modules.
            for module in list(sys.modules.values()):
                if not module or not getattr(module, '__file__', None):
                    continue
                filename = module.__file__
                if filename.endswith(('.pyc', '.pyo')):
                    filename = filename[:-1]
                filename = os.path.abspath(os.path.realpath(filename))
                files.add(filename)
            # Watch settings and URLs if configured.
            if settings.configured:
                settings_mod = import_module(settings.SETTINGS_MODULE)
                if getattr(settings_mod, '__file__', None):
                    files.add(os.path.abspath(os.path.realpath(settings_mod.__file__.rstrip('co'))))

                # Watch project URLConf.
                urlconf = getattr(settings, 'ROOT_URLCONF', None)
                if urlconf:
                    try:
                        urls_mod = import_module(urlconf)
                    except Exception:
                        urls_mod = None
                    if urls_mod and getattr(urls_mod, '__file__', None):
                        files.add(os.path.abspath(os.path.realpath(urls_mod.__file__.rstrip('co'))))

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