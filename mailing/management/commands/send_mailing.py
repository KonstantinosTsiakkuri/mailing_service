from django.core.management.base import BaseCommand, CommandError

from mailing.models import Mailing
from mailing.services import MailingSendError, send_mailing


class Command(BaseCommand):
    help = "Отправляет рассылку по её id: python manage.py send_mailing <id>"

    def add_arguments(self, parser):
        parser.add_argument("mailing_id", type=int, help="id рассылки")

    def handle(self, *args, **options):
        try:
            mailing = Mailing.objects.get(pk=options["mailing_id"])
        except Mailing.DoesNotExist:
            raise CommandError(f"Рассылка с id={options['mailing_id']} не найдена")
        try:
            success, failed = send_mailing(mailing)
        except MailingSendError as error:
            raise CommandError(str(error))
        self.stdout.write(self.style.SUCCESS(f"Рассылка отправлена: успешно {success}, неуспешно {failed}"))
