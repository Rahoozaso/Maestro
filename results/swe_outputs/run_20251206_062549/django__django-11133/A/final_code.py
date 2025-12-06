import datetime
import json
import time
from email.header import Header
from http import HTTPStatus
from urllib.parse import quote, urlencode

from django.conf import settings
from django.core.exceptions import DisallowedRedirect
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.encoding import iri_to_uri
from django.utils.http import http_date
from django.utils.version import PY38

__all__ = [
    'Http404',
    'HttpResponse', 'StreamingHttpResponse', 'HttpResponseRedirect',
    'HttpResponsePermanentRedirect', 'HttpResponseNotModified',
    'HttpResponseBadRequest', 'HttpResponseForbidden',
    'HttpResponseNotFound', 'HttpResponseNotAllowed',
    'HttpResponseGone', 'HttpResponseServerError', 'HttpResponseNotAcceptable',
    'JsonResponse',
]

# Use the system's cgi module, if available, for multipart parsing.
try:  # pragma: no cover -- No need to test the optimization.
    from cgi import parse_header
except ImportError:  # Python 3.8+ on some platforms.
    from email.message import Message as _Message

    def parse_header(line):
        message = _Message()
        message['content-type'] = line
        return message.get_params()[0]


class Http404(Exception):
    pass


class BadHeaderError(ValueError):
    pass


class HttpResponseBase:
    """An HTTP response base class."""

    status_code = HTTPStatus.OK
    reason_phrase = None

    def __init__(self, content_type=None, status=None, reason=None, charset=None):
        self.headers = {}
        self._cookies = None
        self._resource_closers = []
        if status is not None:
            self.status_code = int(status)
        if reason is not None:
            self.reason_phrase = str(reason)
        self._charset = charset
        if content_type is None:
            content_type = 'text/html; charset=%s' % self.charset
        self['Content-Type'] = content_type

    @property
    def charset(self):
        return self._charset or settings.DEFAULT_CHARSET

    @charset.setter
    def charset(self, value):
        self._charset = value
        if 'Content-Type' in self:
            self['Content-Type'] = self['Content-Type'].split(';')[0] + '; charset=%s' % self.charset

    def __iter__(self):
        return self

    def __next__(self):  # pragma: no cover - to be implemented in subclasses.
        raise StopIteration

    # __getitem__ and __setitem__ delegate to header dictionary.
    def __setitem__(self, header, value):
        self.headers[header] = self._convert_to_charset(value)

    def __getitem__(self, header):
        return self.headers[header]

    def __delitem__(self, header):
        del self.headers[header]

    def __contains__(self, header):
        return header in self.headers

    def items(self):
        return self.headers.items()

    def _convert_to_charset(self, value):
        if isinstance(value, str):
            return value
        if isinstance(value, (bytes, bytearray, memoryview)):
            return value.decode(self.charset or 'utf-8')
        return str(value)

    @property
    def cookies(self):
        if self._cookies is None:
            from http.cookies import SimpleCookie
            self._cookies = SimpleCookie()
        return self._cookies

    def set_cookie(self, key, value='', max_age=None, expires=None, path='/',
                   domain=None, secure=False, httponly=False, samesite=None):
        self.cookies[key] = value
        if max_age is not None:
            self.cookies[key]['max-age'] = max_age
        if expires is not None:
            if isinstance(expires, datetime.datetime):
                expires = http_date(time.mktime(expires.timetuple()))
            self.cookies[key]['expires'] = expires
        if path is not None:
            self.cookies[key]['path'] = path
        if domain is not None:
            self.cookies[key]['domain'] = domain
        if secure:
            self.cookies[key]['secure'] = True
        if httponly:
            self.cookies[key]['httponly'] = True
        if samesite:
            self.cookies[key]['samesite'] = samesite

    def delete_cookie(self, key, path='/', domain=None, samesite=None):
        self.set_cookie(key, max_age=0, path=path, domain=domain, samesite=samesite)

    def close(self):
        for closer in self._resource_closers:
            try:
                closer()
            except Exception:
                pass

    def write(self, content):  # pragma: no cover - overridden in subclasses.
        raise OSError('This %s instance is not writable' % self.__class__.__name__)


class HttpResponse(HttpResponseBase):
    """An HTTP response with a string as content."""

    streaming = False

    def __init__(self, content=b"", *args, **kwargs):
        # Normalize buffer-protocol objects like memoryview to bytes so that
        # HttpResponse(memoryview(b"My Content")).content yields b"My Content".
        if isinstance(content, memoryview):
            content = bytes(content)
        else:
            # Preserve existing behavior for str and bytes while allowing other
            # non-string, non-bytes buffer-like objects to be coerced to bytes.
            if not isinstance(content, (bytes, str)):
                try:
                    content = bytes(content)
                except TypeError:
                    # Fall back to existing behavior, which will eventually
                    # treat it as text via str() if appropriate.
                    pass

        super().__init__(*args, **kwargs)
        self.content = content

    @property
    def content(self):
        return b''.join(self._container)

    @content.setter
    def content(self, value):
        # Django's existing normalization path: accept str or bytes-like and
        # store as bytes in the internal container.
        if isinstance(value, str):
            value = value.encode(self.charset)
        elif not isinstance(value, (bytes, bytearray, memoryview)):
            value = str(value).encode(self.charset)
        self._container = [bytes(value)]

    def write(self, content):
        self.content = content

    def tell(self):
        return len(self.content)


class StreamingHttpResponse(HttpResponseBase):
    """An HTTP response with streaming content."""

    streaming = True

    def __init__(self, streaming_content=(), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.streaming_content = streaming_content

    @property
    def content(self):  # pragma: no cover -- not used for streaming responses.
        raise AttributeError("This %s instance has no 'content' attribute. Use 'streaming_content' instead." % self.__class__.__name__)

    @content.setter
    def content(self, value):  # pragma: no cover -- not used for streaming responses.
        raise AttributeError("This %s instance has no 'content' attribute. Use 'streaming_content' instead." % self.__class__.__name__)

    def __iter__(self):
        return iter(self._iterator)

    @property
    def streaming_content(self):
        return self._iterator

    @streaming_content.setter
    def streaming_content(self, value):
        self._iterator = iter(value)


class HttpResponseRedirectBase(HttpResponse):
    allowed_schemes = ['http', 'https']

    def __init__(self, redirect_to, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self['Location'] = self._build_redirect_location(redirect_to)

    def _build_redirect_location(self, redirect_to):
        if '
' in redirect_to or '' in redirect_to:
            raise BadHeaderError("Header values can't contain newlines")

        # If it's a str, assume it's an IRI that requires encoding
        if isinstance(redirect_to, str):
            redirect_to = iri_to_uri(redirect_to)
        else:
            # Bytes or such-like
            redirect_to = redirect_to.decode('utf-8')

        # Check that the scheme is allowed
        scheme = redirect_to.split(':', 1)[0].lower()
        if scheme and scheme not in self.allowed_schemes:
            raise DisallowedRedirect("Unsafe redirect to URL with protocol '%s'" % scheme)

        return redirect_to


class HttpResponseRedirect(HttpResponseRedirectBase):
    status_code = HTTPStatus.FOUND


class HttpResponsePermanentRedirect(HttpResponseRedirectBase):
    status_code = HTTPStatus.MOVED_PERMANENTLY


class HttpResponseNotModified(HttpResponseBase):
    status_code = HTTPStatus.NOT_MODIFIED

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Not-Modified responses MUST NOT include a message-body in the
        # response. (RFC7232 Section 4.1)
        self['Content-Length'] = '0'


class HttpResponseBadRequest(HttpResponse):
    status_code = HTTPStatus.BAD_REQUEST


class HttpResponseForbidden(HttpResponse):
    status_code = HTTPStatus.FORBIDDEN


class HttpResponseNotFound(HttpResponse):
    status_code = HTTPStatus.NOT_FOUND


class HttpResponseNotAllowed(HttpResponse):
    status_code = HTTPStatus.METHOD_NOT_ALLOWED

    def __init__(self, permitted_methods, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self['Allow'] = ', '.join(permitted_methods)


class HttpResponseGone(HttpResponse):
    status_code = HTTPStatus.GONE


class HttpResponseServerError(HttpResponse):
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR


class HttpResponseNotAcceptable(HttpResponse):
    status_code = HTTPStatus.NOT_ACCEPTABLE


class JsonResponse(HttpResponse):
    """An HTTP response class that consumes data to be serialized to JSON."""

    def __init__(self, data, encoder=DjangoJSONEncoder, safe=True, json_dumps_params=None, **kwargs):
        if safe and not isinstance(data, (dict, list, tuple)):
            raise TypeError(
                'In order to allow non-dict objects to be serialized set ' \
                'the safe parameter to False.'
            )
        if json_dumps_params is None:
            json_dumps_params = {}
        kwargs.setdefault('content_type', 'application/json')
        data = json.dumps(data, cls=encoder, **json_dumps_params)
        super().__init__(data, **kwargs)