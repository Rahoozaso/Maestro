from unittest import TestCase


class BaseDisplayMixin:
    """Simulate Django's auto-generated get_FOO_display implementation.

    In Django, when a model field has choices, a get_FOO_display() method is
    generated which returns the human-readable label. This mixin mimics that
    behavior so that we can test overriding semantics without needing Django's
    ORM, settings, or app registry.
    """

    FOO = 1
    BAR = 2
    FOO_BAR_CHOICES = (
        (FOO, "foo"),
        (BAR, "bar"),
    )

    def __init__(self, foo_bar):
        self.foo_bar = foo_bar

    def get_foo_bar_display(self):  # auto-generated-style implementation
        for value, label in self.FOO_BAR_CHOICES:
            if value == self.foo_bar:
                return label
        return str(self.foo_bar)

    def __str__(self):
        # As in Django's Model.__str__, this uses the result of
        # get_foo_bar_display(). The question under test is whether an
        # override of get_foo_bar_display on a subclass is respected.
        return self.get_foo_bar_display()


class FooBar(BaseDisplayMixin):
    """User-level class that overrides get_foo_bar_display.

    In Django, this would be a models.Model subclass overriding the
    auto-generated get_foo_bar_display method. Here we mimic that
    relationship in pure Python.
    """

    def get_foo_bar_display(self):
        # User override: this should take precedence over the base
        # implementation derived from choices.
        return "something"


class GetFieldDisplayOverrideTests(TestCase):
    def test_get_field_display_can_be_overridden(self):
        obj = FooBar(foo_bar=FooBar.FOO)
        # The user-defined get_foo_bar_display should take precedence over the
        # auto-generated implementation based on choices.
        self.assertEqual(obj.get_foo_bar_display(), "something")
        # __str__ should also reflect the overridden method.
        self.assertEqual(str(obj), "something")

    def test_base_mixin_uses_choices_by_default(self):
        # Sanity check: the mixin by itself returns choice labels when there
        # is no override present.
        base_obj = BaseDisplayMixin(foo_bar=BaseDisplayMixin.BAR)
        self.assertEqual(base_obj.get_foo_bar_display(), "bar")
        self.assertEqual(str(base_obj), "bar")