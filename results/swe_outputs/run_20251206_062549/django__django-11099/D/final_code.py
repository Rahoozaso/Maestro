import re

"""Username validators for Django's authentication system.

These validators ensure that usernames contain only allowed characters.
ASCIIUsernameValidator enforces ASCII-only usernames, while
UnicodeUsernameValidator allows any Unicode word characters plus the
symbols '@', '.', '+', and '-'. Both validators use '\A' and '\Z' in
their regular expressions instead of '^' and '$' to avoid a Python
regex quirk where '$' can match a trailing newline.
"""

from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class ASCIIUsernameValidator(RegexValidator):
    """Validate that a username contains only allowed ASCII characters.

    Allowed characters are ASCII letters, digits, and the symbols
    '@', '.', '+', '-', and '_'. The pattern is anchored with '\A' and
    '\Z' to ensure that trailing newlines are rejected.
    """

    regex = r"\A[\w.@+-]+\Z"
    message = _(
        "Enter a valid username. This value may contain only letters, "
        "numbers, and @/./+/-/_ characters."
    )
    flags = re.ASCII


@deconstructible
class UnicodeUsernameValidator(RegexValidator):
    """Validate that a username contains only allowed Unicode characters.

    Allowed characters are Unicode word characters and the symbols
    '@', '.', '+', '-', and '_'. The pattern is anchored with '\A' and
    '\Z' to ensure that trailing newlines are rejected.
    """

    regex = r"\A[\w.@+-]+\Z"
    message = _(
        "Enter a valid username. This value may contain only letters, "
        "numbers, and @/./+/-/_ characters."
    )