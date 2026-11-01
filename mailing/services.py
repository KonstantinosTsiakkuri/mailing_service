from django.core.mail import send_mail
from django.utils import timezone

from mailing.models import Client, Mailing, MailingAttempt


class MailingSendError(Exception):
    """Рассылку нельзя отправить (например, сейчас не время рассылки)."""


def send_mailing(mailing):
    """
    Отправляет письмо каждому получателю рассылки и сохраняет попытки.
    Возвращает кортеж (успешных, неуспешных). Если рассылку сейчас отправлять нельзя - MailingSendError.
    """
    mailing.update_status()
    now = timezone.now()
    if not mailing.start_time <= now <= mailing.end_time:
        raise MailingSendError(
            "Отправка невозможна: текущее время вне периода рассылки "
            f"({timezone.localtime(mailing.start_time):%d.%m.%Y %H:%M} - "
            f"{timezone.localtime(mailing.end_time):%d.%m.%Y %H:%M})"
        )

    attempts = []
    for client in mailing.recipients.all():
        try:
            send_mail(
                subject=mailing.message.subject,
                message=mailing.message.body,
                from_email=None,  # None - взять DEFAULT_FROM_EMAIL из настроек
                recipient_list=[client.email],
                fail_silently=False,
            )
            status = MailingAttempt.STATUS_SUCCESS
            response = "Письмо принято почтовым сервером"
        except Exception as error:
            status = MailingAttempt.STATUS_FAILED
            response = f"{type(error).__name__}: {error}"
        attempts.append(
            MailingAttempt(mailing=mailing, recipient=client, status=status, server_response=response)
        )

    # Все попытки сохраняются одним запросом к БД
    MailingAttempt.objects.bulk_create(attempts)

    success = sum(1 for attempt in attempts if attempt.status == MailingAttempt.STATUS_SUCCESS)
    return success, len(attempts) - success


def get_home_statistics():
    """Показатели для главной страницы: всего рассылок, активных рассылок, всего клиентов."""
    # Статусы хранятся в БД и сами не меняются, поэтому перед подсчётом пересчитываем их
    for mailing in Mailing.objects.all():
        mailing.update_status()
    now = timezone.now()
    return {
        "mailings_total": Mailing.objects.count(),
        "mailings_active": Mailing.objects.filter(
            status=Mailing.STATUS_LAUNCHED, start_time__lte=now, end_time__gte=now
        ).count(),
        "clients_total": Client.objects.count(),
    }
