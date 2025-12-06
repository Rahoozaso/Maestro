from django.db import models
from django.test import TestCase
from django.utils.translation import gettext_lazy as _


class FooBar(models.Model):
    """Model with choices to verify overriding get_FIELD_display works."""

    FOO = 1
    BAR = 2
    FOO_BAR_CHOICES = (
        (FOO, "foo"),
        (BAR, "bar"),
    )

    foo_bar = models.IntegerField(_("foo"), choices=FOO_BAR_CHOICES)

    def __str__(self):
        """Return the custom display value for foo_bar."""
        return self.get_foo_bar_display()

    def get_foo_bar_display(self):
        """Custom override of the auto-generated display method for foo_bar."""
        return "something"


class GetFieldDisplayOverrideTests(TestCase):
    """Tests that user-defined get_FIELD_display overrides the auto-generated one."""

    def test_get_field_display_can_be_overridden(self):
        obj = FooBar(foo_bar=FooBar.FOO)
        # The user-defined get_foo_bar_display should take precedence over the
        # auto-generated implementation based on choices.
        self.assertEqual(obj.get_foo_bar_display(), "something")
        # __str__ should also reflect the overridden method.
        self.assertEqual(str(obj), "something")