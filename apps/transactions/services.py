from decimal import Decimal

from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError

from apps.wallets.models import Wallet
from apps.projects.models import Project
from apps.investments.models import Investment
from apps.notifications.tasks import create_notification
from apps.notifications.models import Notification
from .models import Transaction


class InsufficientFundsError(Exception):
    """Levee quand un wallet n'a pas assez de solde disponible pour l'operation demandee."""
    pass


class TransactionService:
    """
    Couche service : orchestre les operations financieres qui touchent
    PLUSIEURS modeles a la fois (Wallet + Transaction + Investment + Project).

    Chaque methode publique de cette classe est le SEUL point d'entree
    autorise pour executer un mouvement financier reel sur la plateforme.
    """

    @staticmethod
    @db_transaction.atomic
    def deposit(wallet: Wallet, amount: Decimal, description: str = "") -> Transaction:
        """
        Depot de fonds sur le wallet (simule -- integration reelle d'un
        prestataire de paiement hors scope).
        """
        txn = Transaction.objects.create(
            wallet=wallet,
            transaction_type=Transaction.TransactionType.DEPOSIT,
            amount=amount,
            status=Transaction.Status.PENDING,
            description=description or "Depot de fonds",
        )

        locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        locked_wallet.credit(amount, description=f"Depot - {txn.reference}")

        txn.status = Transaction.Status.COMPLETED
        txn.save()
        return txn

    @staticmethod
    @db_transaction.atomic
    def withdraw(wallet: Wallet, amount: Decimal, description: str = "") -> Transaction:
        """
        Retrait de fonds depuis le wallet vers l'exterieur (simule).
        """
        locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        if amount > locked_wallet.available_balance:
            raise InsufficientFundsError(
                f"Solde disponible insuffisant : {locked_wallet.available_balance} disponible, "
                f"{amount} demande."
            )

        txn = Transaction.objects.create(
            wallet=wallet,
            transaction_type=Transaction.TransactionType.WITHDRAWAL,
            amount=amount,
            status=Transaction.Status.PENDING,
            description=description or "Retrait de fonds",
        )

        locked_wallet.debit(amount, description=f"Retrait - {txn.reference}")

        txn.status = Transaction.Status.COMPLETED
        txn.save()
        return txn

    @staticmethod
    @db_transaction.atomic
    def invest(wallet: Wallet, project: Project, amount: Decimal) -> Transaction:
        """
        Un investisseur investit dans un projet :
        1. Verifie que le projet accepte des investissements
        2. Debite le wallet de l'investisseur
        3. Credite current_amount du projet
        4. Trace la transaction, liee au projet
        5. Cree l'Investment correspondant (position durable)
        6. Notifie l'entreprise porteuse (apres commit reel)
        """
        investor_profile = getattr(wallet.user, 'investor_profile', None)
        if investor_profile is None:
            raise ValidationError(
                "Seul un utilisateur avec un profil investisseur peut investir dans un projet."
            )

        if not project.is_open_for_investment:
            raise ValidationError(
                f"Le projet '{project.title}' n'accepte pas d'investissement actuellement "
                f"(statut: {project.get_status_display()})."
            )

        locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        locked_project = Project.objects.select_for_update().get(pk=project.pk)

        if amount > locked_wallet.available_balance:
            raise InsufficientFundsError(
                f"Solde disponible insuffisant : {locked_wallet.available_balance} disponible, "
                f"{amount} demande."
            )

        if locked_project.current_amount + amount > locked_project.funding_goal:
            raise ValidationError(
                "Ce montant depasserait l'objectif de financement du projet."
            )

        txn = Transaction.objects.create(
            wallet=wallet,
            project=project,
            transaction_type=Transaction.TransactionType.INVESTMENT,
            amount=amount,
            status=Transaction.Status.PENDING,
            description=f"Investissement dans {project.title}",
        )

        locked_wallet.debit(amount, description=f"Investissement - {txn.reference}")

        locked_project.current_amount += amount
        locked_project.full_clean()
        locked_project.save()

        Investment.objects.create(
            investor_profile=investor_profile,
            project=project,
            transaction=txn,
            amount=amount,
            status=Investment.Status.ACTIVE,
        )

        txn.status = Transaction.Status.COMPLETED
        txn.save()

        # Notifie l'ENTREPRISE porteuse, apres validation reelle de la transaction.
        db_transaction.on_commit(lambda: create_notification.delay(
            user_id=project.company.user.pk,
            notification_type=Notification.NotificationType.INVESTMENT_RECEIVED,
            title="Nouvel investissement reçu",
            message=f"Vous avez reçu un investissement de {amount} sur le projet '{project.title}'.",
        ))

        return txn