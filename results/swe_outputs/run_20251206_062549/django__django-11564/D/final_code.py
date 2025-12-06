from __future__ import annotations

from urllib.parse import urljoin
from typing import Any

from django.conf import settings
from django.contrib.staticfiles.storage import StaticFilesStorage
from django.core.files.storage import FileSystemStorage
from django.http import HttpRequest
from django.template import Context, Template
from django.test import SimpleTestCase, override_settings, RequestFactory


# --- django/utils/_script_name.py ---


def add_script_name_prefix(url: str, script_name: str | None) -> str:
    """Prefix an absolute URL path with SCRIPT_NAME when appropriate.

    - If ``script_name`` is falsy, ``url`` is returned unchanged.
    - ``script_name`` is normalized to start with ``'/'`` and not end with ``'/'``.
    - If ``url`` already starts with the normalized ``script_name``, it's returned
      unchanged to avoid double-prefixing.
    - Otherwise ``script_name`` is prepended, taking care not to introduce
      duplicate slashes.

    ``url`` is assumed to be an absolute path (i.e. it starts with ``'/'``).
    """
    if not script_name:
        return url

    # Normalize script_name: ensure leading slash, drop trailing slash (except root).
    if not script_name.startswith("/"):
        script_name = "/" + script_name
    if len(script_name) > 1 and script_name.endswith("/"):
        script_name = script_name[:-1]

    # If already prefixed, do nothing.
    if url.startswith(script_name + "/") or url == script_name:
        return url

    # At this point, script_name has no trailing slash (except when it is "/").
    # url is an absolute path starting with "/".
    if script_name == "/":
        # Root prefix doesn't change the URL.
        return url

    return script_name + url


# --- django/templatetags/static.py ---

from django import template
from django.templatetags.static import StaticNode as DjangoStaticNode  # type: ignore


register = template.Library()


class StaticNode(DjangoStaticNode):
    def render(self, context: Context) -> str:
        url = self.url(context)
        # If a request is in the template context and it defines SCRIPT_NAME,
        # prefix the generated static URL accordingly.
        request: HttpRequest | None = context.get("request")  # type: ignore[assignment]
        if request is not None:
            script_name = request.META.get("SCRIPT_NAME") or ""
            if script_name:
                url = add_script_name_prefix(url, script_name)

        if self.varname is None:
            return url
        context[self.varname] = url
        return ""


# --- django/contrib/staticfiles/templatetags/staticfiles.py ---

from django.contrib.staticfiles.templatetags.staticfiles import StaticNode as DjangoStaticFilesStaticNode  # type: ignore


class StaticFilesStaticNode(DjangoStaticFilesStaticNode, StaticNode):
    def render(self, context: Context) -> str:
        # Delegate to the base static tag behavior which is now SCRIPT_NAME-aware.
        url = super().render(context)
        return url


# --- django/core/files/storage.py ---


class ScriptNameFileSystemStorage(FileSystemStorage):
    def url(self, name: str, *, request: HttpRequest | None = None, script_name: str | None = None) -> str:  # type: ignore[override]
        """Return an absolute URL where the file's contents can be accessed.

        If a WSGI SCRIPT_NAME prefix is provided either via the request META
        or explicitly via the script_name argument, that prefix will be
        prepended to the base URL. If neither is provided, behavior is
        unchanged from previous versions.
        """
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")

        # Original URL construction logic (preserved).
        url = urljoin(self.base_url, name.replace("\\", "/"))

        # Apply SCRIPT_NAME if available.
        if request is not None and script_name is None:
            script_name = request.META.get("SCRIPT_NAME") or ""
        if script_name:
            url = add_script_name_prefix(url, script_name)

        return url


# --- django/contrib/staticfiles/storage.py ---


class ScriptNameStaticFilesStorage(StaticFilesStorage, ScriptNameFileSystemStorage):
    def url(
        self,
        name: str,
        *,
        request: HttpRequest | None = None,
        script_name: str | None = None,
        **kwargs: Any,
    ) -> str:  # type: ignore[override]
        """Return the URL for given static file, honoring SCRIPT_NAME if provided."""
        # Delegate to the parent implementation, passing through request and script_name.
        return super().url(name, request=request, script_name=script_name, **kwargs)


# --- tests/template_tests/test_script_name_static.py ---


@override_settings(
    STATIC_URL="/static/",
    MEDIA_URL="/media/",
)
class ScriptNameStaticTests(SimpleTestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def render_template(self, tpl: str, request: HttpRequest | None = None) -> str:
        tmpl = Template(tpl)
        context_data: dict[str, Any] = {}
        if request is not None:
            context_data["request"] = request
        return tmpl.render(Context(context_data)).strip()

    def test_static_tag_with_script_name(self) -> None:
        request = self.factory.get("/", SCRIPT_NAME="/subpath")
        out = self.render_template("{% load static %}{% static 'css/app.css' %}", request)
        # Should start with SCRIPT_NAME + STATIC_URL
        self.assertTrue(out.startswith("/subpath/static/"))
        self.assertTrue(out.endswith("css/app.css"))

    def test_static_tag_without_script_name(self) -> None:
        request = self.factory.get("/")
        out = self.render_template("{% load static %}{% static 'css/app.css' %}", request)
        self.assertEqual(out, "/static/css/app.css")

    def test_static_tag_without_request(self) -> None:
        out = self.render_template("{% load static %}{% static 'css/app.css' %}")
        self.assertEqual(out, "/static/css/app.css")

    @override_settings(INSTALLED_APPS=settings.INSTALLED_APPS + ["django.contrib.staticfiles"])
    def test_contrib_staticfiles_tag_with_script_name(self) -> None:
        request = self.factory.get("/", SCRIPT_NAME="/subpath")
        out = self.render_template("{% load static from staticfiles %}{% static 'css/app.css' %}", request)
        self.assertTrue(out.startswith("/subpath/static/"))
        self.assertTrue(out.endswith("css/app.css"))

    def test_filesystem_storage_url_without_script_name(self) -> None:
        storage = ScriptNameFileSystemStorage(base_url="/media/")
        url = storage.url("img/logo.png")
        self.assertEqual(url, "/media/img/logo.png")

    def test_filesystem_storage_url_with_script_name_via_request(self) -> None:
        storage = ScriptNameFileSystemStorage(base_url="/media/")
        request = self.factory.get("/", SCRIPT_NAME="/subpath")
        url = storage.url("img/logo.png", request=request)
        self.assertEqual(url, "/subpath/media/img/logo.png")

    def test_filesystem_storage_url_with_explicit_script_name(self) -> None:
        storage = ScriptNameFileSystemStorage(base_url="/media/")
        url = storage.url("img/logo.png", script_name="/subpath")
        self.assertEqual(url, "/subpath/media/img/logo.png")

    def test_staticfiles_storage_url_without_script_name(self) -> None:
        storage = ScriptNameStaticFilesStorage(base_url="/static/")
        url = storage.url("js/app.js")
        self.assertEqual(url, "/static/js/app.js")

    def test_staticfiles_storage_url_with_script_name_via_request(self) -> None:
        storage = ScriptNameStaticFilesStorage(base_url="/static/")
        request = self.factory.get("/", SCRIPT_NAME="/subpath")
        url = storage.url("js/app.js", request=request)
        self.assertEqual(url, "/subpath/static/js/app.js")

    def test_staticfiles_storage_url_with_explicit_script_name(self) -> None:
        storage = ScriptNameStaticFilesStorage(base_url="/static/")
        url = storage.url("js/app.js", script_name="/subpath")
        self.assertEqual(url, "/subpath/static/js/app.js")