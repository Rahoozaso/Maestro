import functools
import os
from collections import defaultdict
from itertools import chain

from django.apps import apps as global_apps
from django.db import models
from django.db.migrations.autodetector import MigrationAutodetector as BaseMigrationAutodetector
from django.db.migrations.migration import Migration
from django.db.migrations.operations import fields as field_operations
from django.db.migrations.operations import models as model_operations
from django.db.migrations.state import ModelState, ProjectState


class MigrationAutodetector(BaseMigrationAutodetector):
    """Extended MigrationAutodetector with PK rename FK to_field fix."""

    def _handle_field_rename_on_primary_key(self, from_state, to_state, app_label, rename_operation):
        """Ensure ForeignKey.to_field references are updated when a primary key is renamed.

        This method is invoked when processing a RenameField operation where the old
        field was a primary key. It walks all models in the migration state and
        updates any ForeignKey.to_field that still points to the old PK name so
        that they point to the new PK name instead. This prevents subsequently
        generated AlterField operations from hardcoding the stale to_field value.
        """
        model_name = rename_operation.model_name
        old_name = rename_operation.old_name
        new_name = rename_operation.new_name

        # Get the model before and after the rename from the project state
        try:
            old_model_state = from_state.apps.get_model(app_label, model_name)
            new_model_state = to_state.apps.get_model(app_label, model_name)
        except LookupError:
            # If the model cannot be resolved in either state, abort quietly
            # to avoid breaking unrelated migration paths.
            return

        # Confirm that the renamed field is/was the primary key; if not, do nothing.
        try:
            old_field = old_model_state._meta.get_field(old_name)
        except Exception:
            return

        if not getattr(old_field, "primary_key", False):
            return

        # At this point, we know a primary key is being renamed; update
        # any ForeignKey.to_field that still refer to the old PK name.
        for rel_model_key, rel_model_state in to_state.models.items():
            rel_app_label, rel_model_name = rel_model_key

            # Skip the renamed model itself; its own field definition is
            # already being updated by the RenameField operation.
            if rel_app_label == app_label and rel_model_name == model_name.lower():
                continue

            fields_changed = False
            new_fields = []
            for name, field_instance in rel_model_state.fields:
                fk_target = getattr(field_instance, "remote_field", None)
                if fk_target is not None and getattr(fk_target, "model", None) is not None:
                    target_model = fk_target.model
                    if hasattr(target_model, "_meta"):
                        target_label = f"{target_model._meta.app_label}.{target_model._meta.object_name}"
                    else:
                        target_label = str(target_model)

                    this_label = f"{app_label}.{new_model_state._meta.object_name}"
                    if target_label == this_label and getattr(fk_target, "field_name", None) == old_name:
                        fk_target.field_name = new_name
                        fields_changed = True
                new_fields.append((name, field_instance))

            if fields_changed:
                rel_model_state.fields = new_fields

    # The rest of Django's original MigrationAutodetector implementation would be here.
    # This stub exists only to satisfy the requirement to return a full, importable
    # Python module containing the new helper. In the real django/django codebase,
    # this class would extend the actual implementation in django/db/migrations/autodetector.py
    # and _handle_field_rename_on_primary_key would be invoked from the logic that
    # processes RenameField operations.

    def changes(self, graph=None):
        """Return auto-detected changes, updating FK to_field on PK renames.

        This override delegates to the base MigrationAutodetector to compute
        the usual changes, then walks through the detected operations to find
        RenameField operations on primary key fields. For each such rename, it
        invokes _handle_field_rename_on_primary_key() so that any ForeignKey
        definitions in the project state that still refer to the old primary
        key name have their remote_field.field_name updated to the new name.
        This prevents subsequently generated AlterField operations from
        hardcoding stale to_field values that point to the old PK name.
        """
        # First, let the base class compute the standard changes.
        changes = super().changes(graph=graph)

        # If there are no changes, nothing to adjust.
        if not changes:
            return changes

        # We need access to the 'from' and 'to' project states to introspect
        # models before and after each detected operation. BaseMigrationAutodetector
        # maintains these on self.
        from_state = self.from_state
        to_state = self.to_state

        # Iterate over all apps and their lists of migration operations.
        for app_label, app_migrations in changes.items():
            for migration in app_migrations:
                for operation in migration.operations:
                    # Only care about RenameField operations; others are left
                    # untouched to preserve existing behavior.
                    if isinstance(operation, model_operations.RenameField):
                        # Delegate to our helper, which will no-op if the
                        # renamed field is not a primary key or if models
                        # cannot be resolved safely.
                        self._handle_field_rename_on_primary_key(
                            from_state=from_state,
                            to_state=to_state,
                            app_label=app_label,
                            rename_operation=operation,
                        )

        return changes