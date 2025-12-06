from django.core.checks import run_checks
from django.db import models
from django.test import SimpleTestCase, override_settings


class BaseModel(models.Model):
    class Meta:
        app_label = 'base'
        db_table = 'shared_table'


class App2Model(models.Model):
    class Meta:
        app_label = 'app2'
        db_table = 'shared_table'


class MultiDBRouter:
    """Route BaseModel to 'default' and App2Model to 'other'."""

    def db_for_read(self, model, **hints):
        if model is BaseModel:
            return 'default'
        if model is App2Model:
            return 'other'
        return None

    def db_for_write(self, model, **hints):
        if model is BaseModel:
            return 'default'
        if model is App2Model:
            return 'other'
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'base':
            return db == 'default'
        if app_label == 'app2':
            return db == 'other'
        return None


@override_settings(
    DATABASES={
        'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'},
        'other': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'},
    },
    DATABASE_ROUTERS=['tests.check_framework.test_model_checks_multi_db_table_name.MultiDBRouter'],
)
class DuplicateTableMultiDBTests(SimpleTestCase):

    def test_same_db_table_on_different_databases_is_allowed(self):
        """Identical db_table names routed to different databases must not trigger models.E028."""
        errors = run_checks(tags=None)
        e028_errors = [e for e in errors if e.id == 'models.E028']
        self.assertEqual(e028_errors, [])