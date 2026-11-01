from django.apps import AppConfig


class MailingConfig(AppConfig):
    name = "mailing"

    def ready(self):
        # Подключаем сигналы, которые сбрасывают кэш при изменении данных
        from mailing import signals  # noqa: F401
