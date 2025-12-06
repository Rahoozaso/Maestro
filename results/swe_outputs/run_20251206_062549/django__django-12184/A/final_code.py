import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, MiddlewareNotUsed
from django.http import HttpRequest, HttpResponse
from django.urls import Resolver404, get_resolver
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

logger = logging.getLogger('django.request')


def _get_response_async(request: HttpRequest) -> Awaitable[HttpResponse]:  # pragma: no cover - wrapper
    handler = BaseHandler()
    return handler.get_response_async(request)


class BaseHandler:
    """Base HTTP request handler.

    This is a simplified and slightly adapted version of Django's
    django.core.handlers.base.BaseHandler, with an additional normalization
    layer for view callback arguments to avoid passing duplicate positional
    and keyword arguments originating from optional named regex groups in
    URL patterns.
    """

    _middleware_chain: Optional[Callable[[HttpRequest], Awaitable[HttpResponse]]] = None

    def __init__(self) -> None:
        self._view_middleware: List[Callable] = []
        self._template_response_middleware: List[Callable] = []
        self._exception_middleware: List[Callable] = []
        self.load_middleware()

    @cached_property
    def resolver(self):
        return get_resolver()

    def load_middleware(self) -> None:
        self._view_middleware = []
        self._template_response_middleware = []
        self._exception_middleware = []

        handler = self._get_response_async
        for middleware_path in reversed(settings.MIDDLEWARE):
            middleware = import_string(middleware_path)
            try:
                mw_instance = middleware(handler)
            except MiddlewareNotUsed as exc:
                if settings.DEBUG:
                    logger.debug('MiddlewareNotUsed(%r): %s', middleware_path, exc)
                continue
            if mw_instance is None:
                raise ImproperlyConfigured(
                    'Middleware factory %s returned None.' % middleware_path
                )
            if hasattr(mw_instance, 'process_view'):
                self._view_middleware.insert(0, mw_instance.process_view)
            if hasattr(mw_instance, 'process_template_response'):
                self._template_response_middleware.append(
                    mw_instance.process_template_response
                )
            if hasattr(mw_instance, 'process_exception'):
                self._exception_middleware.append(mw_instance.process_exception)
            handler = mw_instance
        self._middleware_chain = handler

    async def get_response_async(self, request: HttpRequest) -> HttpResponse:
        """Asynchronously get an HttpResponse for the given HttpRequest."""
        if self._middleware_chain is None:
            self.load_middleware()

        response = await self._middleware_chain(request)
        return response

    async def _get_response_async(self, request: HttpRequest) -> HttpResponse:
        """Core response handler used by the middleware chain.

        This method resolves the URL, applies view middleware, and invokes the
        resolved view callback. The key customization is in how the view is
        ultimately invoked: we route the call through _invoke_view() so that
        callback_args and callback_kwargs are normalized, preventing duplicate
        positional/keyword arguments caused by optional named regex groups.
        """
        try:
            resolver_match = self.resolver.resolve(request.path_info)
        except Resolver404 as exc:
            return self.handle_uncaught_exception(request, exc)

        callback = resolver_match.func
        callback_args = list(resolver_match.args)
        callback_kwargs = dict(resolver_match.kwargs)

        # Apply view middleware.
        for middleware_method in self._view_middleware:
            response = middleware_method(
                request,
                callback,
                callback_args,
                callback_kwargs,
            )
            if asyncio.iscoroutine(response):
                response = await response
            if response:
                return response

        # Invoke the view, normalizing args/kwargs to avoid duplicate passing
        # of arguments stemming from optional named regex groups.
        if asyncio.iscoroutinefunction(callback):
            response = await self._invoke_view_async(
                request, callback, callback_args, callback_kwargs
            )
        else:
            response = self._invoke_view(request, callback, callback_args, callback_kwargs)

        # Apply template-response middleware.
        if hasattr(response, 'render'):
            for middleware_method in self._template_response_middleware:
                response = middleware_method(request, response)
                if asyncio.iscoroutine(response):
                    response = await response
        return response

    def handle_uncaught_exception(self, request: HttpRequest, exc: Exception) -> HttpResponse:
        # Simplified error handling placeholder. In real Django, this would
        # delegate to technical/404/500 handlers.
        logger.error('Unhandled exception: %s', exc, exc_info=True)
        from django.http import HttpResponseServerError

        return HttpResponseServerError('Internal Server Error')

    # ------------------------------------------------------------------
    # New helper: normalize args/kwargs and invoke the view.
    # ------------------------------------------------------------------
    def _normalize_callback_args_kwargs(
        self,
        callback: Callable[..., Any],
        callback_args: List[Any],
        callback_kwargs: Dict[str, Any],
    ) -> Tuple[List[Any], Dict[str, Any]]:
        """Normalize callback_args and callback_kwargs before view invocation.

        Goal: prevent a situation where an optional named regex group in the
        URL pattern (e.g. ``(?P<format>(html|json|xml))?``) results in the same
        logical parameter being provided both positionally and by keyword,
        which can cause ``TypeError: ... positional arguments but ... were given``
        for views declared with defaulted parameters like::

            def modules(request, format='html'):
                ...

        Strategy:
        - Inspect the callback's signature.
        - Determine how many positional parameters (excluding *args) the view
          can accept.
        - Trim ``callback_args`` so that no more than this number are passed.
        - This mirrors what Python would naturally allow while ensuring we
          don't exceed the view's positional arity when URL resolution
        - (via regex groups) produced extra positional arguments.

        This is intentionally conservative and does not alter keyword
        arguments provided by the resolver.
        """
        # Fast path: nothing to normalize if there are no positional arguments
        # or no kwargs (the reported bug arises when both are present).
        if not callback_args or not callback_kwargs:
            return callback_args, callback_kwargs

        try:
            import inspect

            sig = inspect.signature(callback)
        except (ValueError, TypeError):
            # Builtins or callables without inspectable signatures: leave as-is.
            return callback_args, callback_kwargs

        params = list(sig.parameters.values())

        # Count how many positional arguments (excluding *args) the view can
        # accept. We don't need to reason about defaults here; Python will
        # handle missing arguments, but we must not exceed this count.
        positional_params: List[inspect.Parameter] = []
        var_positional_seen = False

        for p in params:
            if p.kind is inspect.Parameter.VAR_POSITIONAL:
                var_positional_seen = True
                break
            if p.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            ):
                positional_params.append(p)

        if var_positional_seen:
            # The view accepts *args; over-supplying positional arguments is
            # valid Python, so no normalization is necessary.
            return callback_args, callback_kwargs

        max_positional = len(positional_params)
        if len(callback_args) <= max_positional:
            return callback_args, callback_kwargs

        # Trim extra positional arguments that go beyond what the view can
        # accept (excluding *args). This avoids errors where optional named
        # groups created both a positional entry and a keyword for the same
        # logical argument.
        return callback_args[:max_positional], callback_kwargs

    def _invoke_view(
        self,
        request: HttpRequest,
        callback: Callable[..., Any],
        callback_args: List[Any],
        callback_kwargs: Dict[str, Any],
    ) -> Any:
        """Synchronous view invocation with normalized args/kwargs."""
        norm_args, norm_kwargs = self._normalize_callback_args_kwargs(
            callback, callback_args, callback_kwargs
        )
        return callback(request, *norm_args, **norm_kwargs)

    async def _invoke_view_async(
        self,
        request: HttpRequest,
        callback: Callable[..., Awaitable[Any]],
        callback_args: List[Any],
        callback_kwargs: Dict[str, Any],
    ) -> Any:
        """Asynchronous view invocation with normalized args/kwargs."""
        norm_args, norm_kwargs = self._normalize_callback_args_kwargs(
            callback, callback_args, callback_kwargs
        )
        return await callback(request, *norm_args, **norm_kwargs)