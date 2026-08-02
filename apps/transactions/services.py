from decimal import Decimal

from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError

from apps.wallets.models import Wallet
from apps.projects.models import Project
from apps.investments.models import Investment
from .models import Transaction


class InsufficientFundsError(Exception):
    """Levee quand un wallet n'a pas assez de solde disponible pour l'operation demandee."""
    pass


class TransactionService:
    """
    Couche service : orchestre les operations financieres qui touchent
    PLUSIEURS modeles a la fois (Wallet + Transaction + Investment + Project).
    """

    @staticmethod
    @db_transaction.atomic
    def deposit(wallet: Wallet, amount: Decimal, description: str = "") -> Transaction:
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
        Un investisseur investit dans un projet. Cree ATOMIQUEMENT :
        - le debit du wallet
        - le credit du projet (current_amount)
        - la Transaction (preuve financiere)
        - l'Investment (position durable, liee a la transaction)
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
        return txn
