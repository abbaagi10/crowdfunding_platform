from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import CustomUser
from .utils import send_activation_email


@receiver(post_save, sender=CustomUser)
def send_activation_email_on_creation(sender, instance, created, **kwargs):
    """
    Signal déclenché automatiquement après la sauvegarde d'un CustomUser.
    N'envoie l'email d'activation QUE lors de la création initiale (created=True),
    jamais lors d'une simple mise à jour ultérieure du profil.
    """
    if created and not instance.is_superuser:
        # On n'envoie pas d'email d'activation aux superusers créés via createsuperuser
        send_activation_email(instance)