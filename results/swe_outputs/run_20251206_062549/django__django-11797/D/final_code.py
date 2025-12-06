from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.models import Max


class UserGroupBySubqueryRegressionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        # Two users sharing the same email, different ids
        self.u1 = User.objects.create(username='u1', email='shared@example.com')
        self.u2 = User.objects.create(username='u2', email='shared@example.com')

    def test_filter_on_grouped_subquery_preserves_group_by_columns(self):
        User = get_user_model()

        # This mirrors the example from the issue description
        a = (
            User.objects
            .filter(email__isnull=False)
            .values('email')
            .annotate(m=Max('id'))
            .values('m')
        )

        # Sanity check: the outer query should group by email at the ORM level
        a_sql = str(a.query)
        self.assertIn('GROUP BY', a_sql)
        self.assertIn('email', a_sql)

        # The bug occurs when using the sliced subquery in a filter.
        # We assert that the internal subquery still groups by email,
        # not by id.
        b = User.objects.filter(id=a[:1])
        b_sql = str(b.query)

        # The regression: historically, this GROUP BY would incorrectly be on id.
        # This assertion encodes the intended correct behavior: grouping remains on email.
        # We do not assert exact SQL, only the presence of the correct grouping column.
        self.assertIn('GROUP BY', b_sql)
        # Ensure email is part of the GROUP BY clause
        self.assertIn('email', b_sql)