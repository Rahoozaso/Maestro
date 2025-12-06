from django.core.exceptions import FieldError
from django.db.models import Lookup


class IsNull(Lookup):
    lookup_name = 'isnull'

    def get_prep_lookup(self):
        """Prepare the right-hand side value for the __isnull lookup.

        Only boolean values (True or False) are allowed. Using other
        truthy/falsey values was previously accepted but undocumented and
        may lead to confusing behavior, so it now raises FieldError.
        """
        # Let the parent class perform its normal preparation first,
        # in case it normalizes or validates in a generic way.
        rhs_value = super().get_prep_lookup()

        # Enforce that __isnull only accepts bools. Reject all other
        # types (e.g., 0, 1, '', [], 'true', etc.).
        if not isinstance(rhs_value, bool):
            raise FieldError(
                "The '__isnull' lookup only accepts boolean values (True or False). "
                "Got %r (%s)." % (rhs_value, type(rhs_value).__name__)
            )

        # Existing semantics are preserved:
        #   True  -> IS NULL
        #   False -> IS NOT NULL
        return rhs_value