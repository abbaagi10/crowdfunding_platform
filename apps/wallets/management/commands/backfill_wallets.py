from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.wallets.models import Wallet
from apps.wallets.signals import WALLET_ELIGIBLE_ROLES

User = get_user_model()


class Command(BaseCommand):
    """
    Commande : python manage.py backfill_wallets

    Cree retroactivement un Wallet pour tous les utilisateurs existants
    (INVESTISSEUR ou ENTREPRISE) qui n'en ont pas encore -- typiquement
    les comptes crees AVANT l'ajout de l'app wallets au projet.
    Utile a executer UNE FOIS apres deploiement de cette fonctionnalite.
    """
    help = "Cree un Wallet pour tous les utilisateurs eligibles qui n'en ont pas encore."

    def handle(self, *args, **options):
        eligible_users = User.objects.filter(role__in=WALLET_ELIGIBLE_ROLES)
        created_count = 0

        for user in eligible_users:
            wallet, created = Wallet.objects.get_or_create(user=user)
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Wallet cree pour {user.email}"))

        self.stdout.write(self.style.SUCCESS(
            f"Termine : {created_count} wallet(s) cree(s) sur {eligible_users.count()} utilisateur(s) eligible(s)."
        ))
