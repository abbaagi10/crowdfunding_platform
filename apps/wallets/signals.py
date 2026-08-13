from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Wallet


# Rôles pour lesquels un portefeuille a un sens métier.
# Les administrateurs (SUPERADMIN, USERADMIN) n'investissent jamais
# et ne reçoivent jamais de fonds collectés -- ils n'ont pas besoin de wallet.
WALLET_ELIGIBLE_ROLES = ('INVESTISSEUR', 'ENTREPRISE', 'PLATFORM')


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_wallet_for_new_user(sender, instance, created, **kwargs):
    """
    Crée automatiquement un Wallet vide pour les nouveaux utilisateurs
    dont le rôle a un sens métier pour la gestion de fonds
    (Investisseur ou Entreprise), mais PAS pour les administrateurs.
    """
    if created and instance.role in WALLET_ELIGIBLE_ROLES:
        Wallet.objects.get_or_create(user=instance)
