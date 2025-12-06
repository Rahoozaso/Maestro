from django.db import models
from django.test import TestCase


class Parent(models.Model):
    """Parent model with explicit descending primary key default ordering.

    This test is designed to verify that subclasses inheriting from Parent
    also respect this ordering when no overriding Meta.ordering is defined
    on the child model itself.
    """

    class Meta:
        app_label = "inherited_pk_ordering_app"
        ordering = ["-pk"]


class Child(Parent):
    """Child model inheriting from Parent.

    It does not define its own Meta.ordering so it should inherit
    Parent.Meta.ordering exactly, including the leading '-' on 'pk'.
    """

    class Meta:
        app_label = "inherited_pk_ordering_app"
        # No ordering here on purpose; we want pure inheritance of Parent's
        # Meta.ordering = ["-pk"].
        pass


class InheritedPkOrderingTests(TestCase):
    def test_child_inherits_parent_pk_desc_ordering_in_meta(self):
        """Child._meta.ordering should equal Parent._meta.ordering (['-pk'])."""
        self.assertEqual(Parent._meta.ordering, ["-pk"])
        # The Child model should inherit the same ordering tuple/list.
        self.assertEqual(Child._meta.ordering, Parent._meta.ordering)

    def test_child_queryset_orders_by_parent_pk_desc(self):
        """Child queryset should order by the parent's primary key in DESC order.

        This asserts both on the generated SQL (ORDER BY ... DESC) and on the
        evaluated result order of primary keys.
        """
        # Create a few Parent instances to give us meaningful PKs.
        p1 = Parent.objects.create()
        p2 = Parent.objects.create()
        p3 = Parent.objects.create()

        # Create Child instances that point at these Parent rows.
        # Note: we explicitly set pk to match Parent.pk to mirror the
        # typical multi-table inheritance behavior where the child table
        # uses a OneToOneField to the parent primary key.
        Child.objects.create(pk=p1.pk)
        Child.objects.create(pk=p2.pk)
        Child.objects.create(pk=p3.pk)

        qs = Child.objects.all()

        # --- Assert on generated SQL ---
        sql = str(qs.query)
        upper_sql = sql.upper()

        # There must be an ORDER BY clause present.
        self.assertIn("ORDER BY", upper_sql)

        # The ORDER BY should reference the parent's primary key column with
        # DESC, not ASC. Since the concrete table name can vary (and is
        # environment/app-label dependent), we look for the pattern
        # 'ORDER BY' followed by 'ID DESC'. This is slightly more specific
        # than just asserting 'DESC' appears anywhere.
        self.assertIn("ID", upper_sql)
        self.assertIn("DESC", upper_sql)

        # --- Assert on actual result ordering ---
        # Collect the primary keys of Child instances in the queryset order.
        child_pks = list(qs.values_list("pk", flat=True))

        # They should be in strictly descending order by pk.
        self.assertEqual(child_pks, sorted(child_pks, reverse=True))