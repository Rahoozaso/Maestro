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
        rhs_value = super().get_prep_lookup()

        if not isinstance(rhs_value, bool):
            raise FieldError(
                "The '__isnull' lookup only accepts boolean values (True or False). "
                "Got %r (%s)." % (rhs_value, type(rhs_value).__name__)
            )

        return rhs_value