from django.db import models
from django.test import TestCase


class SimpleModel(models.Model):
    name = models.CharField(max_length=32)


class DeletePkResetTests(TestCase):
    def test_delete_clears_pk_for_model_without_dependencies(self):
        obj = SimpleModel.objects.create(name="foo")
        self.assertIsNotNone(obj.pk)

        obj.delete()

        self.assertIsNone(obj.pk)
        self.assertTrue(obj._state.adding)
        self.assertIsNone(obj._state.db)

    def test_delete_clears_custom_pk(self):
        class CustomPkModel(models.Model):
            custom_id = models.AutoField(primary_key=True)
            name = models.CharField(max_length=32)

            class Meta:
                app_label = SimpleModel._meta.app_label

        obj = CustomPkModel.objects.create(name="bar")
        self.assertIsNotNone(obj.pk)
        self.assertIsNotNone(obj.custom_id)

        obj.delete()

        self.assertIsNone(obj.pk)
        self.assertIsNone(obj.custom_id)