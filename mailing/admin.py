from django.contrib import admin

from mailing.models import Client, Mailing, MailingAttempt, Message

admin.site.register(Client)


admin.site.register(MailingAttempt)


admin.site.register(Mailing)


admin.site.register(Message)
