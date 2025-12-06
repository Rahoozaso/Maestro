from django.db import migrations


def update_proxy_model_permissions(apps, schema_editor):
    """
    Ensure that permissions for proxy models are present, but avoid creating
    duplicate permission rows when proxy models have been recreated, renamed,
    or otherwise changed between releases.

    This function is intentionally defensive: instead of blindly inserting
    permission objects for all proxy models, it first checks whether a
    permission with the same (content_type, codename) combination already
    exists and, if so, skips creation. This prevents IntegrityError on
    databases that already contain the expected permission rows.
    """
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    # We must use the historical AppConfig provided by the migration state.
    app_config = apps.get_app_config('auth')

    # Collect all proxy models that have default permissions.
    proxy_models = [
        model for model in app_config.get_models()
        if model._meta.proxy and not model._meta.auto_created
    ]

    # The default permissions used by Django's permission system.
    default_perms = ('add', 'change', 'delete', 'view')

    for model in proxy_models:
        opts = model._meta
        try:
            content_type = ContentType.objects.get_by_natural_key(
                opts.app_label,
                opts.model,
            )
        except ContentType.DoesNotExist:
            # If the ContentType for this proxy model doesn't exist yet,
            # skip it. A later migration or sync step will create the
            # appropriate permissions when the ContentType becomes available.
            continue

        for perm in default_perms:
            codename = f"{perm}_{opts.model}"
            name = f"Can {perm} {opts.verbose_name_raw}"

            # Defensive existence check to avoid duplicate permission rows
            # when the migration is re-run or the proxy model has been
            # recreated/renamed in a way that left rows behind.
            if Permission.objects.filter(
                content_type=content_type,
                codename=codename,
            ).exists():
                continue

            Permission.objects.create(
                content_type=content_type,
                codename=codename,
                name=name,
            )


def reverse_update_proxy_model_permissions(apps, schema_editor):
    """
    Reverse operation for update_proxy_model_permissions.

    We intentionally do not try to delete permissions here, as doing so could
    remove permissions that have been reassigned to non-proxy models or that
    are relied upon by user code. The reverse function is therefore a noop.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0010_alter_group_name_max_length'),
    ]

    operations = [
        migrations.RunPython(update_proxy_model_permissions, reverse_update_proxy_model_permissions),
    ]