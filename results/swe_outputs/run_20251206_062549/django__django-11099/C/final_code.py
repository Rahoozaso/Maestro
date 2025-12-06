import re

from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class ASCIIUsernameValidator(RegexValidator):
    # Use \A and \Z instead of ^ and $ so that a trailing newline is not
    # considered a valid end-of-string for the username.
    regex = r"\A[\w.@+-]+\Z"
    message = _(
        "Enter a valid username. This value may contain only letters, "
        "numbers, and @/./+/-/_ characters."
    )
    flags = re.ASCII


@deconstructible
class UnicodeUsernameValidator(RegexValidator):
    # Use \A and \Z instead of ^ and $ so that a trailing newline is not
    # considered a valid end-of-string for the username.
    regex = r"\A[\w.@+-]+\Z"
    message = _(
        "Enter a valid username. This value may contain only letters, "
        "numbers, and @/./+/-/_ characters."
    )