from django.core.checks import Error, run_checks
from django.db import models
from django.test import SimpleTestCase, override_settings


def check_max_length_against_choices(app_configs, **kwargs):
    errors = []
    for model in models.get_models(include_auto_created=True):  # type: ignore[attr-defined]
        for field in model._meta.get_fields():
            # Only concrete relational / regular fields have max_length/choices.
            if not hasattr(field, "choices") or not getattr(field, "max_length", None):
                continue

            max_length = field.max_length
            if max_length is None:
                continue

            # choices may be an iterable or a Choices object; iterate generically.
            for choice in field.choices:
                # Grouped choices are of the form (group_name, iterable_of_choices).
                if (
                    isinstance(choice, (list, tuple))
                    and len(choice) == 2
                    and isinstance(choice[1], (list, tuple))
                ):
                    group, group_choices = choice
                    for value, _ in group_choices:
                        if isinstance(value, str) and len(value) > max_length:
                            errors.append(
                                Error(
                                    "'max_length' is too small to fit the longest "
                                    "choice value.",
                                    obj=field,
                                    id="fields.E900",
                                )
                            )
                            break
                    continue

                # Ungrouped choices are (value, label).
                if isinstance(choice, (list, tuple)) and len(choice) >= 1:
                    value = choice[0]
                    if isinstance(value, str) and len(value) > max_length:
                        errors.append(
                            Error(
                                "'max_length' is too small to fit the longest "
                                "choice value.",
                                obj=field,
                                id="fields.E900",
                            )
                        )
                        continue

    return errors


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

        errors = check_max_length_against_choices(None)
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

        errors = check_max_length_against_choices(None)
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

        errors = check_max_length_against_choices(None)
        self.assertTrue(
            any(e.id == "fields.E900" for e in errors),
            msg=(
                "Expected fields.E900 for grouped choices where value "
                "exceeds max_length."
            ),
        )