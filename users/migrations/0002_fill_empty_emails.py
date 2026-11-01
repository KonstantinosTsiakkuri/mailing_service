from django.db import migrations


def fill_empty_emails(apps, schema_editor):
    """Перед тем как сделать email уникальным и логином, заполняем пустые email у существующих пользователей."""
    User = apps.get_model("users", "User")
    for user in User.objects.filter(email=""):
        email = "admin@example.com" if user.is_superuser else f"user{user.pk}@example.com"
        if User.objects.filter(email=email).exists():
            email = f"user{user.pk}@example.com"
        user.email = email
        user.save(update_fields=["email"])


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(fill_empty_emails, migrations.RunPython.noop),
    ]
