from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from mailing.models import Client, Mailing, MailingAttempt
from mailing.services import HOME_STATS_KEY, user_stats_key

# Любое сохранение или удаление этих моделей делает закэшированные показатели неактуальными - сбрасываем их.
# Следующий запрос пересчитает значения заново и снова положит в кэш.


@receiver([post_save, post_delete], sender=Client)
def clear_cache_on_client_change(sender, instance, **kwargs):
    cache.delete(HOME_STATS_KEY)  # на главной есть число клиентов


@receiver([post_save, post_delete], sender=Mailing)
def clear_cache_on_mailing_change(sender, instance, **kwargs):
    cache.delete(HOME_STATS_KEY)
    cache.delete(user_stats_key(instance.owner_id))


@receiver([post_save, post_delete], sender=MailingAttempt)
def clear_cache_on_attempt_change(sender, instance, **kwargs):
    owner_id = Mailing.objects.filter(pk=instance.mailing_id).values_list("owner_id", flat=True).first()
    if owner_id is not None:
        cache.delete(user_stats_key(owner_id))
