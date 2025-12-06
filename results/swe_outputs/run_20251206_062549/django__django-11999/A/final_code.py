from django.db import models
from django.test import TestCase
from django.utils.translation import gettext_lazy as _


class FooBar(models.Model):
    FOO = 1
    BAR = 2
    FOO_BAR_CHOICES = (
        (FOO, 'foo'),
        (BAR, 'bar'),
    )

    foo_bar = models.IntegerField(_('foo'), choices=FOO_BAR_CHOICES)

    def __str__(self):
        return self.get_foo_bar_display()

    def get_foo_bar_display(self):
        return 'something'


class GetFieldDisplayOverrideTests(TestCase):
    def test_get_field_display_can_be_overridden(self):
        obj = FooBar(foo_bar=FooBar.FOO)
        # The user-defined get_foo_bar_display should take precedence over the
        # auto-generated implementation based on choices.
        self.assertEqual(obj.get_foo_bar_display(), 'something')
        # __str__ should also reflect the overridden method.
        self.assertEqual(str(obj), 'something')