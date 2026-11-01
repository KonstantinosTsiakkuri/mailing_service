from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Client(models.Model):
    email = models.EmailField(unique=True, max_length=150, verbose_name="Email")
    full_name = models.CharField(max_length=150, verbose_name="ФИО")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Владелец")

    def __str__(self):
        return f"{self.email},{self.full_name}"

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ["full_name"]
        permissions = [("view_all_clients", "Может просматривать всех клиентов")]


class Message(models.Model):
    subject = models.CharField(max_length=100, verbose_name="Тема письма")
    body = models.TextField(verbose_name="Содержание письма")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Владелец")

    def __str__(self):
        return f"{self.subject}"

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ["subject"]


class Mailing(models.Model):
    STATUS_CREATED = "Создана"
    STATUS_LAUNCHED = "Запущена"
    STATUS_COMPLETED = "Завершена"
    STATUS_CHOICES = [
        (STATUS_CREATED, "Создана"),
        (STATUS_LAUNCHED, "Запущена"),
        (STATUS_COMPLETED, "Завершена"),
    ]
    start_time = models.DateTimeField(verbose_name="Дата начала рассылки")
    end_time = models.DateTimeField(verbose_name="Дата окончания рассылки")
    status = models.CharField(
        verbose_name="Статус рассылки", choices=STATUS_CHOICES, default=STATUS_CREATED, editable=False, max_length=100
    )
    message = models.ForeignKey(Message, on_delete=models.PROTECT, verbose_name="Сообщение рассылки")
    recipients = models.ManyToManyField(Client, verbose_name="Получатели рассылок")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Владелец")

    def __str__(self):
        return f"рассылка {self.message}: {self.status}"

    class Meta:
        verbose_name = "Рассылка"
        verbose_name_plural = "Рассылки"
        ordering = ["status"]
        permissions = [
            ("view_all_mailings", "Может просматривать все рассылки"),
            ("disable_mailing", "Может отключать и включать рассылки"),
        ]

    def update_status(self):
        """
        Пересчитывает статус рассылки по текущему времени
        и сохраняет его в базу, только если он изменился.
        """
        now = timezone.now()
        if now < self.start_time:
            new_status = self.STATUS_CREATED
        elif self.start_time <= now <= self.end_time:
            new_status = self.STATUS_LAUNCHED
        else:
            new_status = self.STATUS_COMPLETED
        if new_status != self.status:
            self.status = new_status
            self.save(update_fields=["status"])

    def clean(self):
        if self.start_time is not None and self.pk is None and self.start_time <= timezone.now():
            raise ValidationError({"start_time": "Дата начала рассылки не может быть в прошлом"})
        if self.start_time is not None and self.end_time is not None and self.start_time >= self.end_time:
            raise ValidationError({"start_time": "Дата начала рассылки должна быть раньше даты  окончания"})


class MailingAttempt(models.Model):
    STATUS_SUCCESS = "Успешно"
    STATUS_FAILED = "Не успешно"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Успешно"),
        (STATUS_FAILED, "Не успешно"),
    ]
    attempt_time = models.DateTimeField(verbose_name="Дата и время попытки", auto_now_add=True)
    status = models.CharField(verbose_name="Статус попытки рассылки", choices=STATUS_CHOICES, max_length=20)
    server_response = models.TextField(verbose_name="Ответ сервера", blank=True)
    mailing = models.ForeignKey(Mailing, verbose_name="Рассылка", on_delete=models.CASCADE, related_name="attempts")
    recipient = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="получатель рассылок",
        related_name="mailing_attempts",
    )

    def __str__(self):
        return f"Попытка рассылки {self.mailing}"

    class Meta:
        verbose_name = "Попытка рассылки"
        verbose_name_plural = "Попытки рассылки"
        ordering = ["-attempt_time"]
