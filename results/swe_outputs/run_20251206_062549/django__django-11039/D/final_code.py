from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState


class Command(BaseCommand):
    help = "Prints the SQL statements for the named migration."  # pragma: no cover - help text

    output_transaction = True

    def add_arguments(self, parser):
        parser.add_argument(
            "app_label",
            help="App label of an application to synchronize the state.",
        )
        parser.add_argument(
            "migration_name",
            help=(
                "Database state will be brought to the state after that "
                "migration. Use the name 'zero' to unapply all migrations."
            ),
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help=(
                'Nominates a database to print the SQL for. Defaults to the '
                '"default" database.'
            ),
        )

    def handle(self, app_label, migration_name, database=DEFAULT_DB_ALIAS, **options):
        connection = connections[database]
        loader = MigrationLoader(connection)

        if app_label not in loader.migrated_apps:
            raise CommandError("App '%s' does not have migrations." % app_label)

        # Find the migration object.
        migration = None
        for key, migration_obj in loader.disk_migrations.items():
            if key[0] != app_label:
                continue
            if key[1] == migration_name or migration_obj.name == migration_name:
                migration = migration_obj
                break
        if migration is None:
            raise CommandError("Migration %s.%s not found." % (app_label, migration_name))

        # Start from the project state just before this migration is applied.
        project_state = loader.project_state((migration.app_label, migration.name), at_end=False)

        # Align sqlmigrate's transaction wrapping behavior with the migration
        # executor and schema editor semantics: only wrap the output when the
        # migration is atomic *and* the database can roll back DDL.
        can_rollback_ddl = getattr(connection.features, "can_rollback_ddl", False)
        self.output_transaction = bool(migration.atomic and can_rollback_ddl)

        with connection.schema_editor(collect_sql=True, atomic=migration.atomic) as schema_editor:
            migration.apply(project_state, schema_editor)

        statements = schema_editor.collected_sql

        if not statements:
            return

        if self.output_transaction:
            self.stdout.write("BEGIN;")
            for statement in statements:
                self.stdout.write("%s;" % statement)
            self.stdout.write("COMMIT;")
        else:
            for statement in statements:
                self.stdout.write("%s;" % statement)