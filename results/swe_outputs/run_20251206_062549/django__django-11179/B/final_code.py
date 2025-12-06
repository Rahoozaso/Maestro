from django.db import DEFAULT_DB_ALIAS, router


class Collector:
    """Track/delete relations of cascade-deleted objects."""

    def __init__(self, using=DEFAULT_DB_ALIAS):
        self.using = using
        # The origin of cascade-deletions: the objects that were explicitly
        # passed to Collector.collect(), plus any others that are deleted along
        # with it via CASCADE.
        self.data = {}
        self.field_updates = {}
        self.dependencies = {}
        self.fast_deletes = set()
        self.can_fast_delete = {}
        self._visited = set()
        self._field_dependencies = {}
        self._instances_with_model_signal = set()
        self._instances_with_signal = set()

    # ... existing Collector implementation ...


def delete(self, using=None):
    """
    Delete the object in the database and reset its state to behave as an
    unsaved instance (no primary key, adding=True, db=None) when the
    deletion is completed.
    """
    assert self.pk is not None, "Cannot delete a %s instance without a primary key" % self.__class__.__name__

    using = using or router.db_for_write(self.__class__, instance=self)
    collector = Collector(using=using)
    collector.collect([self])
    collector.delete()

    # After successful deletion, reset the instance to an unsaved state.
    # Clear the generic pk attribute.
    self.pk = None

    # Also clear the concrete primary key field (e.g., custom_id) so that
    # both obj.pk and obj.<pk_field_name> are None.
    pk_field = self._meta.pk
    if pk_field.attname and hasattr(self, pk_field.attname):
        setattr(self, pk_field.attname, None)

    # Ensure the model state reflects an unsaved instance.
    self._state.adding = True
    self._state.db = None

    return