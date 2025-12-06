from django.core.checks import run_checks
from django.db import models
from django.test import SimpleTestCase, override_settings


class MaxLengthChoicesCheckTests(SimpleTestCase):

    @override_settings(INSTALLED_APPS=["tests.model_fields"])
    def test_error_when_choice_longer_than_max_length(self):
        class InvalidModel(models.Model):
            field = models.CharField(
                max_length=3,
                choices=[("TOO_LONG", "Too long label")],
            )

            class Meta:
                app_label = "tests_model_fields"

        errors = run_checks()
        self.assertTrue(
            any(e.id == "fields.E900" for e in errors),
            msg="Expected fields.E900 when choice value exceeds max_length.",
        )

    @override_settings(INSTALLED_APPS=["tests.model_fields"])
    def test_no_error_when_max_length_sufficient(self):
        class ValidModel(models.Model):
            field = models.CharField(
                max_length=20,
                choices=[("OK", "Label"), ("ANOTHER", "Label 2")],
            )

            class Meta:
                app_label = "tests_model_fields"

        errors = run_checks()
        self.assertFalse(
            any(e.id == "fields.E900" for e in errors),
            msg="Did not expect fields.E900 when max_length is sufficient.",
        )

    @override_settings(INSTALLED_APPS=["tests.model_fields"])
    def test_grouped_choices_supported(self):
        class GroupedChoicesModel(models.Model):
            field = models.CharField(
                max_length=5,
                choices=[
                    ("Group 1", (("OK", "OK"),)),
                    ("Group 2", (("TOO_LONG", "Too long"),)),
                ],
            )

            class Meta:
                app_label = "tests_model_fields"

        errors = run_checks()
        self.assertTrue(
            any(e.id == "fields.E900" for e in errors),
            msg="Expected fields.E900 for grouped choices where value exceeds max_length.",
        )