from __future__ import unicode_literals

import os
from django.utils.translation import ugettext_lazy as _

#######################
# CORE                #
#######################

DEBUG = False

# Whether the framework should propagate raw exceptions rather than catching
# them. This is useful under some testing siutations and should never be used
# on a live site.
DEBUG_PROPAGATE_EXCEPTIONS = False

# Whether to use the "X-Forwarded-Host" header in preference to the
# "Host" header. This should only be enabled if a proxy which sets this
# header is in use.
USE_X_FORWARDED_HOST = False
USE_X_FORWARDED_PORT = False

# People who get code error notifications.
# In the format (("Full Name", "email@example.com"), ("Full Name", "anotheremail@example.com"))
ADMINS = []

# List of IP addresses, as strings, that:
#   * See debug comments, when DEBUG is true
#   * Receive x-headers
INTERNAL_IPS = []

# Local time zone for this installation. All choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name (although not all
# systems may support all possibilities).
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# If you set this to True, Django will use timezone-aware datetimes.
USE_TZ = True

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# Languages we provide translations for, out of the box. A user may choose to
# use a custom LANGUAGES setting which removes some of these languages.
# Thus, Django does not assume that all these languages are always available.
LANGUAGES = [
    ('af', _('Afrikaans')),
    ('ar', _('Arabic')),
    ('ast', _('Asturian')),
    ('az', _('Azerbaijani')),
    ('bg', _('Bulgarian')),
    ('be', _('Belarusian')),
    ('bn', _('Bengali')),
    ('br', _('Breton')),
    ('bs', _('Bosnian')),
    ('ca', _('Catalan')),
    ('cs', _('Czech')),
    ('cy', _('Welsh')),
    ('da', _('Danish')),
    ('de', _('German')),
    ('dsb', _('Lower Sorbian')),
    ('el', _('Greek')),
    ('en', _('English')),
    ('en-au', _('Australian English')),
    ('en-gb', _('British English')),
    ('eo', _('Esperanto')),
    ('es', _('Spanish')),
    ('es-ar', _('Argentinian Spanish')),
    ('es-co', _('Colombian Spanish')),
    ('es-mx', _('Mexican Spanish')),
    ('es-ni', _('Nicaraguan Spanish')),
    ('es-ve', _('Venezuelan Spanish')),
    ('et', _('Estonian')),
    ('eu', _('Basque')),
    ('fa', _('Persian')),
    ('fi', _('Finnish')),
    ('fr', _('French')),
    ('fy', _('Frisian')),
    ('ga', _('Irish')),
    ('gd', _('Scottish Gaelic')),
    ('gl', _('Galician')),
    ('he', _('Hebrew')),
    ('hi', _('Hindi')),
    ('hr', _('Croatian')),
    ('hsb', _('Upper Sorbian')),
    ('hu', _('Hungarian')),
    ('ia', _('Interlingua')),
    ('id', _('Indonesian')),
    ('io', _('Ido')),
    ('is', _('Icelandic')),
    ('it', _('Italian')),
    ('ja', _('Japanese')),
    ('ka', _('Georgian')),
    ('kk', _('Kazakh')),
    ('km', _('Khmer')),
    ('kn', _('Kannada')),
    ('ko', _('Korean')),
    ('lb', _('Luxembourgish')),
    ('lt', _('Lithuanian')),
    ('lv', _('Latvian')),
    ('mk', _('Macedonian')),
    ('ml', _('Malayalam')),
    ('mn', _('Mongolian')),
    ('mr', _('Marathi')),
    ('my', _('Burmese')),
    ('nb', _('Norwegian Bokmål')),
    ('ne', _('Nepali')),
    ('nl', _('Dutch')),
    ('nn', _('Norwegian Nynorsk')),
    ('os', _('Ossetic')),
    ('pa', _('Punjabi')),
    ('pl', _('Polish')),
    ('pt', _('Portuguese')),
    ('pt-br', _('Brazilian Portuguese')),
    ('ro', _('Romanian')),
    ('ru', _('Russian')),
    ('sk', _('Slovak')),
    ('sl', _('Slovenian')),
    ('sq', _('Albanian')),
    ('sr', _('Serbian')),
    ('sr-latn', _('Serbian Latin')),
    ('sv', _('Swedish')),
    ('sw', _('Swahili')),
    ('ta', _('Tamil')),
    ('te', _('Telugu')),
    ('th', _('Thai')),
    ('tr', _('Turkish')),
    ('tt', _('Tatar')),
    ('udm', _('Udmurt')),
    ('uk', _('Ukrainian')),
    ('ur', _('Urdu')),
    ('vi', _('Vietnamese')),
    ('zh-hans', _('Simplified Chinese')),
    ('zh-hant', _('Traditional Chinese')),
]

# Languages using BiDi (right-to-left) layout
LANGUAGES_BIDI = ["he", "ar", "fa", "ur"]

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# If you set this to False, Django will not use format localization to serve
# E.g. numbers and dates in templates.
USE_I18N = True

# If you set this to False, Django will not use timezone-aware datetimes.
# USE_TZ = False

# A secret key for this particular Django installation. Used in secret-key
# hashing algorithms. Set this in your settings, or Django will complain
# loudly.
SECRET_KEY = ''

# Default content type and charset to use for all HttpResponse objects, if a
# MIME type isn't manually specified. These are used by
# django.middleware.common.CommonMiddleware (the default)
DEFAULT_CONTENT_TYPE = 'text/html'
DEFAULT_CHARSET = 'utf-8'

# Encoding used for I18N
FILE_CHARSET = 'utf-8'

# Email address that error messages come from.
SERVER_EMAIL = 'root@localhost'

# Email address that broken link notifications come from.
DEFAULT_FROM_EMAIL = 'webmaster@localhost'

# Whether to send broken-link emails.
SEND_BROKEN_LINK_EMAILS = False

# List of compiled middleware classes, in order.
MIDDLEWARE = []

# List of domains that are recognized as valid for this site.
ALLOWED_HOSTS = []

# If True, Django will check the "Host" header for "ALLOWED_HOSTS".
# Note that if you define your own custom HttpRequest subclass, it might
# disable these host header checks by default.
USE_X_FORWARDED_HOST = False

########## URL Configuration ##########

ROOT_URLCONF = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = None

# Absolute path to the directory where static files will be collected.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = None

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = []

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Example: "http://foo.com/static/admin/"
ADMIN_MEDIA_PREFIX = '/static/admin/'

# List of upload handler classes to be applied in order.
FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]

#############################
# FILE UPLOAD SETTINGS      #
#############################

# The numeric mode (octal) to apply to uploaded files.
# If None, Django has historically relied on the operating system's
# default file mode and the current process umask, which can result in
# inconsistent permissions depending on the upload handler and platform.
#
# To provide a consistent, secure default for FileSystemStorage uploads,
# Django now defaults this to 0o644. You can override this setting to
# match your deployment's needs.
FILE_UPLOAD_PERMISSIONS = 0o644

# The numeric mode (octal) to apply to directories created for file
# uploads.
FILE_UPLOAD_DIRECTORY_PERMISSIONS = None

# The directory to store uploaded files.
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
MEDIA_URL = ''

# Maximum size, in bytes, of a request before it will be streamed to the
# file system instead of handled by the memory upload handler.
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # i.e. 2.5 MB

# Directory where uploaded files larger than FILE_UPLOAD_MAX_MEMORY_SIZE will
# be stored.
FILE_UPLOAD_TEMP_DIR = None

# If set to True, uploaded files will be stored with a temporary name and
# renamed to the final name after the upload is complete.
FILE_UPLOAD_USE_TEMP_FILE = False

# Default format to use for date fields.
DATE_FORMAT = 'N j, Y'

# Default format to use for datetime fields.
DATETIME_FORMAT = 'N j, Y, P'

# Default format to use for time fields.
TIME_FORMAT = 'P'

# Default formats to use when parsing dates from input fields.
DATE_INPUT_FORMATS = [
    '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y',  # '2006-10-25', '10/25/2006', '10/25/06'
]

# Default formats to use when parsing times from input fields.
TIME_INPUT_FORMATS = [
    '%H:%M:%S', '%H:%M',  # '14:30:59', '14:30'
]

# Default formats to use when parsing datetimes from input fields.
DATETIME_INPUT_FORMATS = [
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
]

# ... the remainder of the global settings file would continue here ...