import os
import time

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.management import call_command
from django.db import router, transaction
from django.utils.six import StringIO
from django.utils.six.moves import input


class BaseDatabaseCreation(object):
    """Base class encapsulating database creation and test DB helpers."""

    # This dictionary maps Field objects to their associated database column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__ before being output.
    # If a column type is set to None, it won't be included in the output.
    data_types = {}

    # This dictionary maps Field objects to their associated SQL, as strings.
    # This SQL is used to alter existing columns when it's not safe to simply
    # change the column type. Column-type strings can contain format strings;
    # they'll be interpolated against the values of Field.__dict__ before being
    # output.
    # For example, the GenericIPAddressField uses this for conversion between
    # ipv4 and ipv6 databases.
    data_type_check_constraints = {}

    def __init__(self, connection):
        self.connection = connection

    def _consume_sql(self, sql, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params or [])

    def _get_test_db_name(self):
        """Internal implementation - returns the name of the test DB."""
        return self.connection.settings_dict['TEST']['NAME'] or self._get_test_db_name_from_settings()

    def _get_test_db_name_from_settings(self):
        """Return the 'NAME' setting for the test DB."""
        if self.connection.settings_dict['NAME'] == '':
            return 'test_%s' % self.connection.alias
        return 'test_%s' % self.connection.settings_dict['NAME']

    def _create_test_db(self, verbosity=1, autoclobber=False, serialize=True):
        """Internal implementation - create the test db tables."""
        if verbosity >= 1:
            test_db_repr = '' if self.connection.settings_dict['NAME'] == '' else ' (' + self.connection.settings_dict['NAME'] + ')'
            print("Creating test database for alias '%s'%s..." % (self.connection.alias, test_db_repr))

        self._create_test_db(verbosity, autoclobber)

        if serialize:
            self.connection._test_serialized_contents = self.serialize_db_to_string()

        call_command(
            'migrate',
            verbosity=max(verbosity - 1, 0),
            interactive=False,
            database=self.connection.alias,
            run_syncdb=True,
        )
        return self.connection.settings_dict['NAME']

    def _destroy_test_db(self, test_database_name, verbosity=1):
        """Internal implementation - remove the test db tables."""
        if verbosity >= 1:
            print("Destroying test database for alias '%s'..." % self.connection.alias)
        self._destroy_test_db(test_database_name, verbosity)

    def set_as_test_mirror(self, primary_settings_dict):
        """Configure this database as a test mirror of the given primary DB."""
        self.connection.settings_dict['NAME'] = primary_settings_dict['NAME']

    def serialize_db_to_string(self):
        """Serialize all data in the database into a JSON string."""

        def get_objects():
            """Yield all non-proxy model instances that should be serialized."""
            for app_config in apps.get_app_configs():
                if (
                    not router.allow_migrate(self.connection.alias, app_config.label)
                    or app_config.models_module is None
                    or app_config.label == 'contenttypes'
                ):
                    continue
                for model in app_config.get_models():
                    if not model._meta.proxy and router.allow_migrate_model(self.connection.alias, model):
                        queryset = model._default_manager.using(self.connection.alias).order_by(model._meta.pk.name)
                        for obj in queryset.iterator():
                            yield obj

        out = StringIO()
        serializers.serialize("json", get_objects(), indent=None, stream=out)
        return out.getvalue()

    def deserialize_db_from_string(self, data):
        """Reload the database with data from a serialized JSON string.

        The entire deserialization is wrapped in a single transaction so that
        inter-object dependencies (e.g., foreign keys) are satisfied without
        causing integrity errors during intermediate saves.
        """
        data = StringIO(data)
        with transaction.atomic(using=self.connection.alias):
            for obj in serializers.deserialize("json", data, using=self.connection.alias):
                obj.save()

    def _get_database_display_str(self, verbosity, database_name):
        """Return display string for a test database."""
        return database_name

    def _clone_test_db(self, number, verbosity=1, autoclobber=False, keepdb=False):
        """Internal implementation - duplicate the test db tables."""
        source_database_name = self.connection.settings_dict['NAME']
        if verbosity >= 1:
            print("Creating test database for alias '%s_%s'..." % (self.connection.alias, number))
        self._clone_test_db(source_database_name, number, verbosity, keepdb)

    def _destroy_test_db(self, test_database_name, verbosity=1):
        """Internal implementation - remove the cloned test db tables."""
        if verbosity >= 1:
            print("Destroying test database for alias '%s'..." % self.connection.alias)
        self._destroy_test_db(test_database_name, verbosity)