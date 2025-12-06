from django.db import migrations


def update_proxy_model_permissions(apps, schema_editor):
    """Recreate permissions for proxy models if needed.

    This migration was introduced to fix a bug where permissions for proxy
    models weren't created. However, attempting to recreate permissions can
    fail with an IntegrityError on projects where the permissions already
    exist (e.g. when proxy models were recreated, renamed, or migrations were
    squashed/reapplied).

    To avoid this, rely on the historical app registry only to determine which
    proxy models exist, and then create the default permissions *only* for
    those (content_type, codename) pairs that are currently missing.
    Existing rows are left untouched.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")

    # Use the historical AppConfig from the migration state.
    auth_app_config = apps.get_app_config("auth")

    # Default permissions created by Django for each model.
    default_perms = ("add", "change", "delete", "view")

    # Collect all proxy models from the historical auth app config.
    proxy_models = [
        model
        for model in auth_app_config.get_models()
        if model._meta.proxy and not model._meta.auto_created
    ]

    for model in proxy_models:
        opts = model._meta
        try:
            content_type = ContentType.objects.get_by_natural_key(
                opts.app_label, opts.model
            )
        except ContentType.DoesNotExist:
            # If the ContentType doesn't exist in this historical state,
            # skip it. Another migration (or the modern state) will handle
            # creating the appropriate permissions once the ContentType
            # exists.
            continue

        for action in default_perms:
            codename = f"{action}_{opts.model}"
            name = f"Can {action} {opts.verbose_name_raw}"

            # Avoid creating duplicate permissions if they already exist,
            # which would otherwise raise an IntegrityError on databases
            # where these rows are already present (for example, after
            # renaming/recreating proxy models or re-running migrations).
            if Permission.objects.filter(
                content_type=content_type, codename=codename
            ).exists():
                continue

            Permission.objects.create(
                content_type=content_type,
                codename=codename,
                name=name,
            )


def reverse_update_proxy_model_permissions(apps, schema_editor):
    """No-op reverse migration.

    Permissions created here might be relied upon by user code or may have
    been reassigned to non-proxy models. Deleting them on reverse could break
    production instances, so this operation is intentionally left empty.
    """
    # Intentionally left as a no-op.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0010_alter_group_name_max_length"),
    ]

    operations = [
        migrations.RunPython(
            update_proxy_model_permissions,
            reverse_update_proxy_model_permissions,
        ),
    ]