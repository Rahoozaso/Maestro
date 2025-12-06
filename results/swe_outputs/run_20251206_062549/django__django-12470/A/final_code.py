from django.db import models
from django.test import TestCase


class Parent(models.Model):
    class Meta:
        ordering = ["-pk"]


class Child(Parent):
    pass


class InheritedPkOrderingTests(TestCase):
    def test_child_respects_parent_pk_desc_ordering(self):
        # Create a few instances to make ordering meaningful
        p1 = Parent.objects.create()
        p2 = Parent.objects.create()
        Child.objects.create(pk=p1.pk)
        Child.objects.create(pk=p2.pk)

        qs = Child.objects.all()
        # Assert that the generated SQL contains DESC on the parent's PK column
        sql = str(qs.query)
        # The exact table/column naming can vary by app label, but we expect
        # ORDER BY "<parent_table>"."id" DESC rather than ASC.
        upper_sql = sql.upper()
        self.assertIn("ORDER BY", upper_sql)
        self.assertIn("DESC", upper_sql)
        # Additionally, confirm that evaluation respects DESC order by PK
        pks = list(qs.values_list("pk", flat=True))
        self.assertEqual(pks, sorted(pks, reverse=True))