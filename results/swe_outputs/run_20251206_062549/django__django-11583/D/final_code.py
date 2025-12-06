import functools
import itertools
import logging
import os
import signal
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path
from types import FrameType
from typing import Callable, Dict, Iterable, Iterator, List, Optional, Set, Tuple

from django.conf import settings
from django.utils import six
from django.utils.functional import cached_property

logger = logging.getLogger(__name__)


# ----- File watching utilities -----

try:
    import pywatchman
except ImportError:  # pragma: no cover
    pywatchman = None


def _check_errors(fn):
    """Decorator: log and ignore errors from watchman client calls."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive; errors just logged
            logger.debug("Watchman error: %s", exc, exc_info=True)
            return None

    return wrapper


class WatchmanUnavailable(RuntimeError):
    pass


class BaseReloader(object):
    def __init__(self):
        self.extra_files: Set[Path] = set()
        self._stop = False

    def watch_file(self, path):
        self.extra_files.add(Path(path))

    def watched_files(self) -> Iterable[Path]:  # pragma: no cover - interface
        raise NotImplementedError

    def tick(self):  # pragma: no cover - interface
        raise NotImplementedError

    def run(self, main_func: Callable[[], None]):
        self._stop = False
        thread = threading.Thread(target=main_func, name="django-main-thread")
        thread.daemon = True
        thread.start()

        while not self._stop:
            for _ in self.tick():
                pass

    def stop(self):
        self._stop = True


class StatReloader(BaseReloader):
    SLEEP_TIME = 1

    def __init__(self):
        super(StatReloader, self).__init__()
        self._mtimes: Dict[Path, float] = {}

    def watched_files(self) -> Iterable[Path]:
        from django.utils.autoreload import iter_all_python_module_files

        yield from iter_all_python_module_files()
        yield from self.extra_files

    def tick(self) -> Iterator[None]:
        has_changes = False
        for filepath, mtime in self.snapshot_files():
            previous_mtime = self._mtimes.get(filepath)
            if previous_mtime is None:
                self._mtimes[filepath] = mtime
                continue
            if previous_mtime < mtime:
                logger.debug("File changed: %s", filepath)
                has_changes = True
                break

        if has_changes:
            self.stop()
        time.sleep(self.SLEEP_TIME)
        yield

    def snapshot_files(self) -> Iterator[Tuple[Path, float]]:
        for file in self.watched_files():
            try:
                mtime = file.stat().st_mtime
            except OSError:
                continue
            yield file, mtime


class WatchmanReloader(BaseReloader):  # pragma: no cover - requires watchman
    def __init__(self):
        super(WatchmanReloader, self).__init__()
        self.client = pywatchman.client()
        self.roots = set()
        self._subscription_counter = itertools.count()
        self._subscriptions = {}

    @_check_errors
    def _watch_project(self, path: str):
        return self.client.query('watch-project', path)

    @_check_errors
    def _subscribe(self, root: str, subscription_name: str, expression):
        self.client.query('subscribe', root, subscription_name, expression)

    @_check_errors
    def _unsubscribe(self, root: str, subscription_name: str):
        self.client.query('unsubscribe', root, subscription_name)

    @_check_errors
    def _recv(self):
        return self.client.receive()

    def watched_files(self) -> Iterable[Path]:
        from django.utils.autoreload import iter_all_python_module_files

        yield from iter_all_python_module_files()
        yield from self.extra_files

    def _update_watches(self):
        paths = set()
        for file in self.watched_files():
            try:
                paths.add(str(file.parent))
            except ValueError:
                # Guard against invalid paths from the filesystem.
                continue

        new_roots = paths - self.roots
        removed_roots = self.roots - paths

        for root in removed_roots:
            self._unsubscribe(root, self._subscriptions.pop(root))
            self.roots.remove(root)

        for root in new_roots:
            result = self._watch_project(root)
            if not result:
                continue
            watch = result['watch']
            if 'relative_path' in result:
                root = os.path.join(watch, result['relative_path'])
            subscription_name = 'django-reload-%s' % next(self._subscription_counter)
            self._subscribe(watch, subscription_name, {
                'expression': ['anyof', ['name', '*.py', 'wholename'], ['name', '*.pyc', 'wholename']],
                'fields': ['name'],
            })
            self.roots.add(root)
            self._subscriptions[root] = subscription_name

    def tick(self) -> Iterator[None]:
        self._update_watches()
        response = self._recv()
        if not response:
            time.sleep(0.1)
            yield
            return
        if response.get('subscription') in self._subscriptions.values():
            self.stop()
        yield


# ----- Module/file iteration helpers -----

_error_files: Set[Path] = set()


def iter_modules_and_files(modules, extra_files: Iterable[Path]) -> Set[Path]:
    """Return a set of all module and extra file paths to watch.

    Guard against pathlib.Path.resolve() raising ValueError (e.g. "embedded
    null byte") which can occur for broken symlinks, unusual mounts, or other
    OS/filesystem issues. In such cases, the offending path is skipped so the
    autoreloader does not crash.
    """
    results: Set[Path] = set()

    for module in modules:
        if not getattr(module, '__file__', None):
            continue
        # Module paths may be .py/.pyc or packages; reuse existing behavior
        # but make the resolution robust against ValueError.
        try:
            path = Path(module.__file__)
        except TypeError:
            # Some modules might have non-path-like __file__.
            continue
        try:
            resolved = path.resolve().absolute()
        except ValueError:
            # Protect against "embedded null byte" and any other
            # resolution-related ValueError from pathlib / os.readlink.
            _error_files.add(path)
            continue
        results.add(resolved)

    for file in extra_files:
        try:
            path = Path(file)
        except TypeError:
            # Extra files might not be path-like; skip invalid entries.
            continue
        try:
            resolved = path.resolve().absolute()
        except ValueError:
            # Same safeguard for AUTORELOAD_EXTRA_FILES.
            _error_files.add(path)
            continue
        results.add(resolved)

    return results


def iter_all_python_module_files() -> Set[Path]:
    """Yield all file paths corresponding to imported modules."""
    modules = list(sys.modules.values())
    extra_files: Set[Path] = getattr(settings, 'AUTORELOAD_EXTRA_FILES', set())
    return iter_modules_and_files(modules, extra_files)


# ----- Public API -----


def get_reloader() -> BaseReloader:
    if pywatchman is not None:
        try:
            return WatchmanReloader()
        except WatchmanUnavailable:
            pass
    return StatReloader()


def restart_with_reloader():
    new_environ = os.environ.copy()
    new_environ['RUN_MAIN'] = 'true'

    args = [sys.executable] + sys.argv
    if sys.platform == 'win32':
        # Windows does not pass the return code of the child process.
        # A more elaborate workaround is needed here, see #18546.
        os.spawnve(os.P_NOWAIT, sys.executable, args, new_environ)
        sys.exit(0)
    else:
        os.execve(sys.executable, args, new_environ)


def run_with_reloader(main_func, *args, **kwargs):
    reloader = get_reloader()

    def start_django(reloader, main_func, *args, **kwargs):
        main_func(*args, **kwargs)

    def inner_run():
        try:
            autoreload_started = False
            while True:
                if not autoreload_started:
                    logger.info("Watching for file changes with %s", reloader.__class__.__name__)
                    autoreload_started = True
                try:
                    reloader.run(lambda: start_django(reloader, main_func, *args, **kwargs))
                except KeyboardInterrupt:
                    # Exit the loop.
                    break
                else:
                    logger.info("Detected code changes, reloading...")
                    restart_with_reloader()
        finally:
            reloader.stop()

    if os.environ.get('RUN_MAIN') == 'true':
        # Main process restarted by the reloader.
        main_func(*args, **kwargs)
    else:
        inner_run()