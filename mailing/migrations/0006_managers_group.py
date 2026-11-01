from django.contrib.auth.management import create_permissions
from django.db import migrations

MANAGER_GROUP_NAME = "Менеджеры"

# (приложение, код права), которые нужны менеджеру
MANAGER_PERMISSIONS = [
    ("mailing", "view_all_clients"),
    ("mailing", "view_all_mailings"),
    ("mailing", "disable_mailing"),
    ("users", "view_all_users"),
    ("users", "block_user"),
]


def create_managers_group(apps, schema_editor):
    # Права Django обычно создаёт уже после всех миграций, а нам они нужны прямо сейчас - создаём вручную
    for app_label in ("mailing", "users"):
        app_config = apps.get_app_config(app_label)
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    group, _ = Group.objects.get_or_create(name=MANAGER_GROUP_NAME)
    for app_label, codename in MANAGER_PERMISSIONS:
        permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
        group.permissions.add(permission)


def delete_managers_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=MANAGER_GROUP_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("mailing", "0005_roles_and_permissions"),
        ("users", "0004_roles_and_permissions"),
    ]

    operations = [
        migrations.RunPython(create_managers_group, delete_managers_group),
    ]
