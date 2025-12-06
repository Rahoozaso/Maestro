# Dedicated SQLite DATABASES settings for test_sqlite module.
# These settings are intentionally scoped to this module to reproduce and
# guard against SQLite locking issues when using persistent test databases
# with --keepdb and multiple database aliases.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'TEST': {
            # Explicit file name to ensure isolation from the default in-memory
            # or other test configurations.
            'NAME': 'test_default.sqlite3',
        },
    },
    'other': {
        'ENGINE': 'django.db.backends.sqlite3',
        'TEST': {
            # Use a separate file per alias to avoid SQLite 'database is locked'
            # errors when tests open multiple connections.
            'NAME': 'test_other.sqlite3',
        },
    },
}

# If this module is imported in a context where Django's settings are already
# configured, we avoid mutating global settings. Instead, tests that need
# these DATABASES should explicitly refer to this module-level DATABASES
# where appropriate (e.g., via override_settings in the test body).