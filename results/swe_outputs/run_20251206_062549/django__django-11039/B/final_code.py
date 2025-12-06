from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections, DEFAULT_DB_ALIAS
from django.test import override_settings, SimpleTestCase


class SqlMigrateTransactionTests(SimpleTestCase):
    databases = {DEFAULT_DB_ALIAS}

    @override_settings(MIGRATION_MODULES={})
    def test_sqlmigrate_non_atomic_when_cannot_rollback_ddl(self):
        connection = connections[DEFAULT_DB_ALIAS]

        # Use a known built-in app and its initial migration which is atomic
        # by default. The behavior under test is controlled via
        # can_rollback_ddl, not the migration's own atomic flag.
        app_label = "contenttypes"
        migration_name = "0001_initial"

        with mock.patch.object(connection.features, "can_rollback_ddl", False):
            with mock.patch("sys.stdout") as mock_stdout:
                call_command("sqlmigrate", app_label, migration_name, database=DEFAULT_DB_ALIAS)

        output = "".join("".join(call.args[0]) for call in mock_stdout.write.call_args_list)

        # When can_rollback_ddl is False, output should not be wrapped in
        # BEGIN/COMMIT even if the migration is atomic.
        self.assertNotIn("BEGIN;", output)
        self.assertNotIn("COMMIT;", output)
        # But SQL statements themselves should still be present.
        self.assertIn("CREATE TABLE", output)