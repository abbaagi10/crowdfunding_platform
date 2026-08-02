from decimal import Decimal

from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError

from apps.wallets.models import Wallet
from apps.projects.models import Project
from .models import Transaction


class InsufficientFundsError(Exception):
    """Levee quand un wallet n'a pas assez de solde disponible pour l'operation demandee."""
    pass


class TransactionService:
    """
    Couche service : orchestre les operations financieres qui touchent
    PLUSIEURS modeles a la fois (Wallet + Transaction + eventuellement Project).

    Chaque methode publique de cette classe est le SEUL point d'entree
    autorise pour executer un mouvement financier reel sur la plateforme --
    aucune vue, aucun autre code ne doit manipuler wallet.credit()/debit()
    directement en dehors d'ici, pour garantir que CHAQUE mouvement de solde
    est systematiquement accompagne d'une Transaction tracee.
    """

    @staticmethod
    @db_transaction.atomic
    def deposit(wallet: Wallet, amount: Decimal, description: str = "") -> Transaction:
        """
        Depot de fonds sur le wallet (ex: rechargement depuis une carte bancaire,
        simule pour l'instant -- l'integration reelle d'un PSP est hors scope ici).
        """
        # 1. Trace l'INTENTION avant d'agir (voir justification ci-dessus)
        txn = Transaction.objects.create(
            wallet=wallet,
            transaction_type=Transaction.TransactionType.DEPOSIT,
            amount=amount,
            status=Transaction.Status.PENDING,
            description=description or "Depot de fonds",
        )

        try:
            # 2. Verrouille la ligne wallet pour la duree de la transaction SQL,
            # empeche une operation concurrente de lire un solde perime.
            locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
            locked_wallet.credit(amount, description=f"Depot - {txn.reference}")

            # 3. Confirme le succes
            txn.status = Transaction.Status.COMPLETED
            txn.save()
        except ValidationError as e:
            # atomic() annule TOUT le bloc (y compris la creation de txn ci-dessus)
            # des qu'une exception non geree remonte -- mais ici on VEUT garder
            # une trace de l'echec plutot que de tout annuler silencieusement.
            # On relve donc l'exception pour laisser atomic() rollback la partie
            # wallet, MAIS on gere le cas dans la vue pour informer l'utilisateur.
            raise

        return txn

    @staticmethod
    @db_transaction.atomic
    def withdraw(wallet: Wallet, amount: Decimal, description: str = "") -> Transaction:
        """
        Retrait de fonds depuis le wallet vers l'exterieur (ex: virement bancaire,
        simule ici -- integration PSP reelle hors scope).
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
        1. Verifie que le projet accepte des investissements (is_open_for_investment)
        2. Debite le wallet de l'investisseur
        3. Credite current_amount du projet
        4. Trace la transaction, liee au projet

        C'est l'operation la plus critique de la plateforme : elle touche
        DEUX entites financieres distinctes (wallet investisseur + projet)
        et DOIT etre parfaitement atomique.
        """
        if not project.is_open_for_investment:
            raise ValidationError(
                f"Le projet '{project.title}' n'accepte pas d'investissement actuellement "
                f"(statut: {project.get_status_display()})."
            )

        # Verrouille le wallet ET le projet pour la duree de la transaction --
        # empeche deux investissements simultanes de causer une incoherence
        # sur current_amount (meme raisonnement que pour le wallet).
        locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        locked_project = Project.objects.select_for_update().get(pk=project.pk)

        if amount > locked_wallet.available_balance:
            raise InsufficientFundsError(
                f"Solde disponible insuffisant : {locked_wallet.available_balance} disponible, "
                f"{amount} demande."
            )

        # Empeche de depasser l'objectif de financement (regle metier)
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

        txn.status = Transaction.Status.COMPLETED
        txn.save()
        return txn
