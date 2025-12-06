import copy
import functools
import os
import re
import sys
import types
import warnings
from collections.abc import Iterable, Mapping
from pathlib import Path
from pprint import pformat
from traceback import TracebackException
from typing import Any, Dict, List, Optional, Set

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.template import Context, Engine, TemplateDoesNotExist, loader
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.module_loading import import_string
from django.utils.version import get_docs_version

HIDDEN_SETTINGS = re.compile("TOKEN|PASSWORD|SECRET|PROFANITIES_LIST|SIGNATURE")


def cleanse_setting(key: str, value: Any, seen: Optional[Set[int]] = None) -> Any:
    """Return a cleaned version of setting *value* for the given key.

    This implementation recursively walks nested containers (dicts and
    other non-string iterables) so that values associated with secret-like
    keys are masked even in deeply nested structures. It preserves common
    container types and is resilient to cyclic references.
    """
    # If the *current* key looks sensitive, mask the whole value.
    if HIDDEN_SETTINGS.search(str(key)):
        return "********************"

    if seen is None:
        seen = set()

    obj_id = id(value)
    if obj_id in seen:
        # Prevent infinite recursion on self-referential structures.
        return "********************"
    seen.add(obj_id)

    # Dict-like objects: cleanse by key.
    if isinstance(value, Mapping):
        cleaned: Dict[Any, Any] = {}
        for k, v in value.items():
            k_str = str(k)
            if HIDDEN_SETTINGS.search(k_str):
                cleaned[k] = "********************"
            else:
                cleaned[k] = cleanse_setting(k_str, v, seen)
        return cleaned

    # Non-string, non-bytes iterables (e.g. list, tuple, set, frozenset).
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        if isinstance(value, list):
            return [cleanse_setting(key, item, seen) for item in value]
        if isinstance(value, tuple):
            return tuple(cleanse_setting(key, item, seen) for item in value)
        if isinstance(value, set):
            return {cleanse_setting(key, item, seen) for item in value}
        if isinstance(value, frozenset):
            return frozenset(
                cleanse_setting(key, item, seen) for item in value
            )
        # Fallback for other iterable types (e.g. custom containers).
        try:
            return type(value)(cleanse_setting(key, item, seen) for item in value)
        except Exception:
            # If reconstruction fails, return a list to ensure we at least
            # cleanse contents instead of leaking secrets.
            return [cleanse_setting(key, item, seen) for item in value]

    # Primitive or non-iterable value, not under a secret key.
    return value


class SafeExceptionReporterFilter:
    """Base filter to replace sensitive values with stars.

    This filter is used for cleaning request data and Django settings before
    they are shown in technical 500 debug pages, ensuring that potentially
    sensitive values such as passwords, tokens, and secrets are not exposed.
    """

    def get_post_parameters(self, request):
        if request is None:
            return {}
        return request.POST

    def get_cookies(self, request):
        if request is None:
            return {}
        return request.COOKIES

    def get_meta(self, request):
        if request is None:
            return {}
        return request.META

    def is_active(self, request):
        """Return whether this filter should be applied for *request*.

        Subclasses may override this to disable filtering based on request
        attributes (for example, user permissions).
        """
        return True

    def get_safe_request(self, request):
        """Return a cloned request with sensitive POST parameters redacted."""
        if request is None:
            return None

        request = self._clone_request(request)

        if not self.is_active(request):
            return request

        if request.method == "POST":
            sensitive_post_parameters = getattr(
                request, "sensitive_post_parameters", set()
            )
            cleansed = request.POST.copy()
            for key in cleansed:
                if key in sensitive_post_parameters or HIDDEN_SETTINGS.search(key):
                    cleansed[key] = "********************"
            request.POST = cleansed
        return request

    def _clone_request(self, request):
        """Return a shallow copy of *request* with mutable attributes copied."""
        if request is None:
            return None
        request = copy.copy(request)
        for attr in ("GET", "POST", "COOKIES", "META"):  # pragma: no branch
            if hasattr(request, attr):
                setattr(request, attr, getattr(request, attr).copy())
        return request

    def get_safe_settings(self):
        """Return a dict of settings with sensitive values redacted.

        The redaction is performed using :func:`cleanse_setting`, which
        recursively walks nested containers to ensure sensitive values are
        masked even in deeply-nested structures.
        """
        settings_dict: Dict[str, Any] = {}
        for k in dir(settings):
            if k.isupper():
                settings_dict[k] = cleanse_setting(k, getattr(settings, k))
        return settings_dict


def technical_500_response(request, exc_type, exc_value, tb, status_code=500):
    """Create a technical server error response.

    The last line of the traceback is highlighted as the most relevant part.
    If the request is AJAX, a plain-text traceback is returned; otherwise an
    HTML technical 500 page is rendered.
    """
    reporter = ExceptionReporter(request, exc_type, exc_value, tb)
    if request is not None and request.headers.get("x-requested-with") == "XMLHttpRequest":
        text = reporter.get_traceback_text()
        return HttpResponse(text, status=status_code, content_type="text/plain")
    html = reporter.get_traceback_html()
    return HttpResponse(html, status=status_code, content_type="text/html")


class ExceptionReporter:
    """Placeholder for Django's ExceptionReporter implementation.

    In the real Django codebase, this class generates the technical 500
    debug pages (HTML and plain text). It is omitted here because the
    current task focuses on settings cleansing behavior.
    """

    def __init__(self, *args, **kwargs):  # pragma: no cover - placeholder
        pass

    def get_traceback_text(self) -> str:  # pragma: no cover - placeholder
        return ""

    def get_traceback_html(self) -> str:  # pragma: no cover - placeholder
        return ""