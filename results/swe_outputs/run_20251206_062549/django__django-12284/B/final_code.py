from django.db import models
from django.test import TestCase


class AbstractBase(models.Model):
    FOO_CHOICES = [
        ("A", "output1"),
        ("B", "output2"),
    ]
    field_foo = models.CharField(max_length=254, choices=FOO_CHOICES)

    class Meta:
        abstract = True


class Child(AbstractBase):
    FOO_CHOICES = [
        ("A", "output1"),
        ("B", "output2"),
        ("C", "output3"),
    ]
    field_foo = models.CharField(max_length=254, choices=FOO_CHOICES)


class Sibling(AbstractBase):
    """Control model that does not override the field to ensure original behavior remains."""

    name = models.CharField(max_length=50, blank=True)


class InheritedChoicesDisplayTests(TestCase):
    databases = {"default"}

    def test_inherited_choices_still_work(self):
        obj = Child.objects.create(field_foo="A")
        self.assertEqual(obj.get_field_foo_display(), "output1")
        obj.field_foo = "B"
        obj.save(update_fields=["field_foo"])
        self.assertEqual(obj.get_field_foo_display(), "output2")

    def test_extended_choices_on_child(self):
        obj = Child.objects.create(field_foo="C")
        # Prior to the fix, this would incorrectly return "C".
        self.assertEqual(obj.get_field_foo_display(), "output3")

    def test_base_behavior_for_sibling_without_override(self):
        # Ensure that a subclass that does not override the field
        # still uses the base class choices correctly.
        obj = Sibling.objects.create(field_foo="A", name="test")
        self.assertEqual(obj.get_field_foo_display(), "output1")
        obj.field_foo = "B"
        obj.save(update_fields=["field_foo"])
        self.assertEqual(obj.get_field_foo_display(), "output2")