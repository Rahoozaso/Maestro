import os
import django
from django.conf import settings

# Minimal settings configuration so that models.Model can be subclassed
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="test-key",
        INSTALLED_APPS=[
            "tests_app",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
    )

from django.apps import AppConfig, apps


class TestsAppConfig(AppConfig):
    name = "tests_app"
    label = "tests_app"


# Register the app config if not already present
if not apps.apps_ready:
    apps.populate([TestsAppConfig("tests_app", __name__)])

# Now that settings and apps are ready, set up Django
if not django.apps.apps.ready:
    django.setup()

from django.db import models, transaction
import unittest


class SimpleModel(models.Model):
    name = models.CharField(max_length=32)

    class Meta:
        app_label = "tests_app"


class CustomPkModel(models.Model):
    custom_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=32)

    class Meta:
        app_label = "tests_app"


class DeletePkResetTests(unittest.TestCase):
    def setUp(self):
        # Ensure database tables exist for our models.
        # In a real Django project, migrations would handle this; here we use schema_editor.
        from django.db import connection

        existing_tables = set(connection.introspection.table_names())
        with connection.schema_editor() as schema_editor:
            if SimpleModel._meta.db_table not in existing_tables:
                schema_editor.create_model(SimpleModel)
            if CustomPkModel._meta.db_table not in existing_tables:
                schema_editor.create_model(CustomPkModel)

    def tearDown(self):
        # Clean up rows between tests to avoid interference.
        SimpleModel.objects.all().delete()
        CustomPkModel.objects.all().delete()

    def test_delete_clears_pk_for_model_without_dependencies(self):
        obj = SimpleModel.objects.create(name="foo")
        self.assertIsNotNone(obj.pk)

        # Use a transaction to ensure the delete hits the DB
        with transaction.atomic():
            obj.delete()

        # After deletion, the instance should behave as unsaved: pk is None.
        self.assertIsNone(obj.pk)
        self.assertTrue(obj._state.adding)
        self.assertIsNone(obj._state.db)

    def test_delete_clears_custom_pk(self):
        obj = CustomPkModel.objects.create(name="bar")
        self.assertIsNotNone(obj.pk)
        self.assertIsNotNone(obj.custom_id)

        with transaction.atomic():
            obj.delete()

        # Both the generic pk and the concrete PK field should be None.
        self.assertIsNone(obj.pk)
        self.assertIsNone(obj.custom_id)


if __name__ == "__main__":
    unittest.main()