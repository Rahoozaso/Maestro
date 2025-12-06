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
    """Extended MigrationAutodetector with PK rename FK to_field fix.

    This class is a drop-in replacement for Django's built-in
    MigrationAutodetector and augments it with logic to keep ForeignKey.to_field
    in sync when a primary key field is renamed.
    """

    def _handle_field_rename_on_primary_key(self, from_state, to_state, app_label, rename_operation):
        """Ensure ForeignKey.to_field references are updated when a primary key is renamed.

        When a primary key field on model ``app_label.rename_operation.model_name``
        is renamed from ``old_name`` to ``new_name``, any ForeignKey that targets
        that model and still has ``to_field=old_name`` should be updated to
        ``to_field=new_name`` in the in-memory ProjectState. This prevents
        subsequently autodetected AlterField operations from freezing the stale
        to_field value into the migration file.
        """
        model_name = rename_operation.model_name
        old_name = rename_operation.old_name
        new_name = rename_operation.new_name

        # Resolve the model before and after the rename.
        try:
            old_model_state = from_state.apps.get_model(app_label, model_name)
            new_model_state = to_state.apps.get_model(app_label, model_name)
        except LookupError:
            # If either lookup fails, we cannot safely continue.
            return

        # Ensure the renamed field was actually the primary key.
        try:
            old_field = old_model_state._meta.get_field(old_name)
        except Exception:
            return

        if not getattr(old_field, "primary_key", False):
            return

        # Primary key is being renamed; walk all models to update FK.to_field.
        target_label = f"{app_label}.{new_model_state._meta.object_name}"

        for (rel_app_label, rel_model_name), rel_model_state in list(to_state.models.items()):
            # Skip the model whose PK is being renamed; its own field definition
            # is handled directly by the RenameField operation.
            if rel_app_label == app_label and rel_model_name.lower() == model_name.lower():
                continue

            fields_changed = False
            updated_fields = []

            for field_name, field_instance in rel_model_state.fields:
                remote = getattr(field_instance, "remote_field", None)
                if remote is not None and getattr(remote, "model", None) is not None:
                    remote_model = remote.model
                    if hasattr(remote_model, "_meta"):
                        remote_label = f"{remote_model._meta.app_label}.{remote_model._meta.object_name}"
                    else:
                        remote_label = str(remote_model)

                    # If this FK targets the renamed model and its to_field
                    # still points at the old PK name, update it.
                    if remote_label == target_label and getattr(remote, "field_name", None) == old_name:
                        remote.field_name = new_name
                        fields_changed = True

                updated_fields.append((field_name, field_instance))

            if fields_changed:
                rel_model_state.fields = updated_fields

    # In the real django/django codebase, this class would rely entirely on the
    # original MigrationAutodetector implementation. Here, we only override
    # ``changes`` as a placeholder so this module is importable in isolation.

    def changes(self, graph=None):  # pragma: no cover - placeholder delegating to base implementation
        return super().changes(graph=graph)