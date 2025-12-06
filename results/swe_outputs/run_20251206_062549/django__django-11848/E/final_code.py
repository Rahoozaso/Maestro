import base64
import datetime
import re
from binascii import Error as BinasciiError
from email.utils import parsedate_tz
from urllib.parse import quote, unquote

from django.utils.functional import keep_lazy_text
from django.utils.regex_helper import _lazy_re_compile

ETAG_ANY = "*"

MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()

# RFC 7231, appendix D.
BAD_HEADER_VALUE_RE = _lazy_re_compile(r"[\x00-\x1F\x7F\(\)<>@,;:\\"/\[\]?={} \t]")


def urlquote(url, safe="/"):
    """A version of urllib.parse.quote() that can operate on bytes and str."""
    return quote(url, safe=safe)


@keep_lazy_text
def urlquote_plus(url, safe=""):
    """A version of urllib.parse.quote_plus() that can operate on bytes and str."""
    return quote(url, safe=safe, encoding="utf-8", errors="strict").replace(" ", "+")


@keep_lazy_text
def urlunquote(quoted_url):
    """A wrapper for urllib.parse.unquote() that supports lazy strings."""
    return unquote(quoted_url)


@keep_lazy_text
def urlunquote_plus(quoted_url):
    """A wrapper for urllib.parse.unquote_plus() that supports lazy strings."""
    return unquote(quoted_url.replace("+", " "))


def urlencode(query, doseq=False):
    """A version of urllib.parse.urlencode() that's safe for UTF-8 strings."""
    if hasattr(query, "items"):
        query = query.items()
    return "&".join(
        "%s=%s" % (quote(str(k)), quote(str(v)))
        for k, v in (query if doseq else ((k, v) for k, v in query))
    )


def http_date(epoch_seconds=None):
    """Return the current date and time formatted for use in HTTP headers."""
    if epoch_seconds is None:
        dt = datetime.datetime.utcnow()
    else:
        dt = datetime.datetime.utcfromtimestamp(epoch_seconds)
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


def parse_http_date(date):
    """Parse an HTTP-date as defined by RFC 7231 section 7.1.1.1.

    Supported formats:
    * RFC 1123: 'Sun, 06 Nov 1994 08:49:37 GMT'
    * RFC 850:  'Sunday, 06-Nov-94 08:49:37 GMT'
    * asctime:  'Sun Nov  6 08:49:37 1994'

    For RFC 850 dates using a two-digit year, this function interprets the
    year according to RFC 7231: any resulting year that would be more than
    50 years in the future is instead mapped to the most recent past year
    that has the same last two digits.
    """
    if date is None:
        return None

    # First, try the standard library parser to get a 9-tuple + offset.
    timetuple = parsedate_tz(date)
    if timetuple is None:
        return None

    # timetuple: (year, month, day, hour, minute, second, wday, yday, dst, tzoffset)
    year, month, day, hour, minute, second, wday, yday, dst, tzoffset = timetuple

    # Detect RFC 850 two-digit year format.
    # RFC 850 example: 'Sunday, 06-Nov-94 08:49:37 GMT'
    # We consider it RFC 850 if:
    # - original string has a comma followed by a space (day-name),
    # - and a hyphen-separated day-month-year part with a 2-digit year.
    is_rfc850_two_digit = False
    try:
        # Quick structural check without full re-parse: look for weekday and hyphen date.
        # This is intentionally conservative to avoid misclassifying other formats.
        if "," in date and "-" in date.split(",", 1)[1]:
            # Split off the day-name part after the comma.
            after_comma = date.split(",", 1)[1].strip()
            # Expect something like '06-Nov-94 ...'
            date_part = after_comma.split(" ", 1)[0]
            parts = date_part.split("-")
            if len(parts) == 3 and len(parts[2]) == 2:
                is_rfc850_two_digit = True
    except Exception:
        # On any parsing heuristic failure, fall back to treating as non-RFC850.
        is_rfc850_two_digit = False

    if is_rfc850_two_digit and 0 <= year <= 99:
        # Apply RFC 7231 50-year sliding window for two-digit years.
        # We find the full year with the given last two digits that is
        # closest to the current year, but not more than 50 years in the future.
        current_year = datetime.date.today().year
        yy = year  # two-digit year from parser

        # Compute the candidate year in the same century as current_year.
        base_century = current_year - (current_year % 100)
        candidate = base_century + yy

        # If candidate is more than 50 years in the future, roll back 100 years
        # to the most recent past year with the same last two digits.
        if candidate - current_year > 50:
            candidate -= 100

        year = candidate

    # At this point, 'year' is a full year, with RFC 850 two-digit years
    # normalized relative to the current year when appropriate.

    try:
        dt = datetime.datetime(year, month, day, hour, minute, second)
    except (OverflowError, ValueError):
        return None

    if tzoffset is None:
        # Assume UTC if no timezone is provided, per RFC 7231 HTTP-date semantics.
        tzoffset = 0

    timestamp = int((dt - datetime.datetime(1970, 1, 1)).total_seconds()) - tzoffset
    return timestamp


def parse_http_date_safe(date):
    """Convert an HTTP date string to a Python datetime object.

    Return None if the input is invalid or represents a time before the epoch.
    """
    try:
        timestamp = parse_http_date(date)
    except Exception:
        return None
    if timestamp is None:
        return None
    if timestamp < 0:
        return None
    return datetime.datetime.utcfromtimestamp(timestamp)


def quote_etag(etag):
    """Quote an ETag if it isn't already quoted."""
    if etag.startswith("W/"):
        etag = "W/" + quote_etag(etag[2:])
    elif not (etag.startswith('"') and etag.endswith('"')):
        etag = '"%s"' % etag
    return etag


def parse_etags(etags):
    """Parse a comma-separated list of ETags."""
    if not etags:
        return []
    return [e.strip() for e in etags.split(',')]


def parse_etag_header(header):
    """
    Parse an HTTP ETag header received from a client.

    Return a list of ETag values, or [ETAG_ANY] if the header value is
    "*".
    """
    if not header:
        return []
    header = header.strip()
    if header == ETAG_ANY:
        return [ETAG_ANY]
    return [e.strip() for e in header.split(',') if e.strip()]


def quote_etag_header(etags):
    """Quote a list of ETags for use in an HTTP header."""
    return ', '.join(quote_etag(etag) for etag in etags)


def http_date_safe(epoch_seconds=None):
    """Return an HTTP date string, or None on an invalid input."""
    try:
        return http_date(epoch_seconds)
    except (OverflowError, ValueError, OSError):  # OSError on Windows.
        return None


def is_same_domain(host, pattern):
    """Test if the host is a subdomain of pattern."""
    host = host.lower()
    pattern = pattern.lower()
    return host == pattern or host.endswith('.' + pattern)


def is_safe_url(url, allowed_hosts, require_https=False):
    """
    Return ``True`` if the url is a safe redirection (i.e. it doesn't point to
    a different host and uses a safe scheme).
    """
    if not url:
        return False
    url = url.strip()
    # Chrome treats \ as / in paths. While this isn't necessarily a problem, it
    # is surprising behavior. So, normalize the URL.
    url = url.replace('\\', '/')
    # Check if the URL is absolute.
    if re.match(r'^https?://', url):
        # Parse the URL.
        scheme, netloc = url.split('://', 1)[0:2]
        # Check if the scheme is safe.
        if scheme not in ['http', 'https']:
            return False
        # Check if the netloc is safe.
        if not any(is_same_domain(netloc, host) for host in allowed_hosts):
            return False
        # Check if HTTPS is required.
        if require_https and scheme != 'https':
            return False
    return True


def base36_to_int(s):
    """Convert a base36 string to an int."""
    return int(s, 36)


def int_to_base36(i):
    """Convert an integer to a base36 string."""
    chars = '0123456789abcdefghijklmnopqrstuvwxyz'
    if i < 0:
        raise ValueError("Negative base36 conversion input.")
    if i == 0:
        return '0'
    base36 = ''
    while i != 0:
        i, mod = divmod(i, 36)
        base36 = chars[mod] + base36
    return base36


def urlsafe_base64_encode(s):
    """Encode a bytestring in URL-safe base64 format."""
    return base64.urlsafe_b64encode(s).rstrip(b'=').decode('ascii')


def urlsafe_base64_decode(s):
    """Decode a URL-safe base64 string."""
    s = s.encode('ascii')  # base64 encoding works on bytes.
    s += b'=' * (-len(s) % 4)  # Pad with '=' to make the length a multiple of 4.
    try:
        return base64.urlsafe_b64decode(s)
    except (BinasciiError, ValueError):
        return b''


def parse_header_parameters(line):
    """
    Parse a header like Content-Disposition: foo; bar="baz" into a dict.
    """
    parts = line.split(';')
    params = {}
    for part in parts[1:]:
        if '=' in part:
            key, value = part.split('=', 1)
            params[key.strip().lower()] = value.strip().strip('"')
    return params


def is_valid_header_value(value):
    """
    Validate the value of an HTTP header.

    This function ensures that the header value doesn't contain characters not
    allowed by RFC 7230 section 3.2.
    """
    if not value:
        return False
    return not BAD_HEADER_VALUE_RE.search(value)