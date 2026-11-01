from django.conf import settings
from django.db import migrations


def assign_owner(apps, schema_editor):
    """Привязывает уже существующие клиентов, сообщения и рассылки к суперпользователю."""
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    superuser = User.objects.filter(is_superuser=True).order_by("pk").first()

    for model_name in ("Client", "Message", "Mailing"):
        model = apps.get_model("mailing", model_name)
        records = model.objects.filter(owner__isnull=True)
        if not records.exists():
            continue
        if superuser is None:
            raise RuntimeError(
                "Есть записи без владельца, но нет суперпользователя. "
                "Создайте его командой createsuperuser и повторите migrate."
            )
        records.update(owner=superuser)


class Migration(migrations.Migration):
    dependencies = [
        ("mailing", "0002_add_owner"),
        ("users", "0003_email_login"),
    ]

    operations = [
        migrations.RunPython(assign_owner, migrations.RunPython.noop),
    ]
