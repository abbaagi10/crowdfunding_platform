# apps/transactions/services.py - Version corrigée

from decimal import Decimal, ROUND_HALF_UP
import logging
from django.utils import timezone
from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError

from apps.wallets.models import Wallet
from apps.projects.models import Project
from apps.investments.models import Investment
from apps.notifications.tasks import create_notification
from apps.notifications.models import Notification
from .models import Transaction

logger = logging.getLogger(__name__)


class InsufficientFundsError(Exception):
    """Levee quand un wallet n'a pas assez de solde disponible pour l'operation demandee."""
    pass


class TransactionService:
    """
    Couche service : orchestre les operations financieres qui touchent
    PLUSIEURS modeles a la fois (Wallet + Transaction + Investment + Project).
    """

    @staticmethod
    def _round_to_two_decimals(value: Decimal) -> Decimal:
        """
        Arrondir une valeur à 2 décimales.
        """
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    @db_transaction.atomic
    def deposit(wallet: Wallet, amount: Decimal, description: str = "") -> Transaction:
        """
        Depot de fonds sur le wallet.
        """
        # Arrondir le montant
        amount = TransactionService._round_to_two_decimals(amount)

        logger.info(f"Deposit - Wallet: {wallet.id}, Amount: {amount}")

        txn = Transaction.objects.create(
            wallet=wallet,
            source_wallet=wallet,
            destination_wallet=wallet,
            transaction_type=Transaction.TransactionType.DEPOSIT,
            amount=amount,
            amount_net=amount,
            status=Transaction.Status.PENDING,
            description=description or "Depot de fonds",
        )

        locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        locked_wallet.credit(amount, description=f"Depot - {txn.reference}")

        txn.status = Transaction.Status.COMPLETED
        txn.completed_at = timezone.now()
        txn.save()

        logger.info(f"Deposit completed - Transaction: {txn.reference}")
        return txn

    @staticmethod
    @db_transaction.atomic
    def withdraw(wallet: Wallet, amount: Decimal, description: str = "") -> Transaction:
        """
        Retrait de fonds depuis le wallet.
        """
        # Arrondir le montant
        amount = TransactionService._round_to_two_decimals(amount)

        logger.info(f"Withdraw - Wallet: {wallet.id}, Amount: {amount}")

        locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        if amount > locked_wallet.available_balance:
            raise InsufficientFundsError(
                f"Solde disponible insuffisant : {locked_wallet.available_balance} disponible, "
                f"{amount} demande."
            )

        txn = Transaction.objects.create(
            wallet=wallet,
            source_wallet=wallet,
            destination_wallet=wallet,
            transaction_type=Transaction.TransactionType.WITHDRAWAL,
            amount=amount,
            amount_net=amount,
            status=Transaction.Status.PENDING,
            description=description or "Retrait de fonds",
        )

        locked_wallet.debit(amount, description=f"Retrait - {txn.reference}")

        txn.status = Transaction.Status.COMPLETED
        txn.completed_at = timezone.now()
        txn.save()

        logger.info(f"Withdraw completed - Transaction: {txn.reference}")
        return txn

    @staticmethod
    @db_transaction.atomic
    def invest(wallet: Wallet, project: Project, amount: Decimal) -> Transaction:
        """
        Un investisseur investit dans un projet.
        """
        # Arrondir le montant
        amount = TransactionService._round_to_two_decimals(amount)

        logger.info(f"Invest - Wallet: {wallet.id}, Project: {project.id}, Amount: {amount}")

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
            source_wallet=wallet,
            destination_wallet=wallet,
            project=project,
            transaction_type=Transaction.TransactionType.INVESTMENT,
            amount=amount,
            amount_net=amount,
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
        txn.completed_at = timezone.now()
        txn.save()

        db_transaction.on_commit(lambda: create_notification.delay(
            user_id=project.company.user.pk,
            notification_type=Notification.NotificationType.INVESTMENT_RECEIVED,
            title="Nouvel investissement reçu",
            message=f"Vous avez reçu un investissement de {amount} sur le projet '{project.title}'.",
        ))

        logger.info(f"Invest completed - Transaction: {txn.reference}")
        return txn


class WalletTransferService:
    """
    Service pour les transferts entre wallets (wallet-to-wallet).
    """
    FEE_RATE = Decimal('0.50')  # 0.5% de frais

    @staticmethod
    def _round_to_two_decimals(value: Decimal) -> Decimal:
        """
        Arrondir une valeur à 2 décimales.
        """
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    @db_transaction.atomic
    def transfer(
        source_user,
        destination_user,
        amount: Decimal,
        description: str = "",
        fee_rate: Decimal = None
    ) -> Transaction:
        """
        Transférer des fonds entre deux utilisateurs.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Normaliser et arrondir le montant
        if isinstance(amount, (int, float, str)):
            amount = Decimal(str(amount))
        
        # 🔥 ARRONDIR À 2 DÉCIMALES
        amount = WalletTransferService._round_to_two_decimals(amount)

        if fee_rate is None:
            fee_rate = WalletTransferService.FEE_RATE

        logger.info(f"Transfer - Source: {source_user.email}, Destination: {destination_user.email}")
        logger.info(f"Transfer - Amount: {amount}, Fee rate: {fee_rate}%")

        # Validation des utilisateurs
        if source_user == destination_user:
            raise ValidationError("Vous ne pouvez pas vous transférer à vous-même.")

        # Récupérer les wallets avec lock
        try:
            source_wallet = Wallet.objects.select_for_update().get(user=source_user)
        except Wallet.DoesNotExist:
            raise ValidationError(f"Wallet de {source_user.email} non trouvé.")

        try:
            destination_wallet = Wallet.objects.select_for_update().get(user=destination_user)
        except Wallet.DoesNotExist:
            raise ValidationError(f"Wallet de {destination_user.email} non trouvé.")

        logger.info(f"Transfer - Source wallet: {source_wallet.id}, Balance: {source_wallet.balance}")
        logger.info(f"Transfer - Destination wallet: {destination_wallet.id}, Balance: {destination_wallet.balance}")

        # Vérifier les fonds disponibles
        if amount > source_wallet.available_balance:
            raise InsufficientFundsError(
                f"Solde insuffisant. Disponible: {source_wallet.available_balance} FCFA, "
                f"Demandé: {amount} FCFA"
            )

        # Calculer les frais
        fee_amount = (amount * fee_rate) / Decimal('100')
        amount_net = amount - fee_amount

        # 🔥 ARRONDIR LES FRAIS ET LE MONTANT NET À 2 DÉCIMALES
        fee_amount = WalletTransferService._round_to_two_decimals(fee_amount)
        amount_net = WalletTransferService._round_to_two_decimals(amount_net)

        logger.info(f"Transfer - Fee: {fee_amount}, Net amount: {amount_net}")

        # Créer la transaction
        txn = Transaction.objects.create(
            wallet=source_wallet,
            source_wallet=source_wallet,
            destination_wallet=destination_wallet,
            transaction_type=Transaction.TransactionType.TRANSFER,
            amount=amount,
            amount_net=amount_net,
            fee_amount=fee_amount,
            fee_rate=fee_rate,
            status=Transaction.Status.PENDING,
            description=description or f"Transfert vers {destination_user.email}",
            metadata={
                'source_email': source_user.email,
                'destination_email': destination_user.email,
                'source_user_id': source_user.id,
                'destination_user_id': destination_user.id,
                'fee_rate': str(fee_rate),
                'fee_amount': str(fee_amount),
            }
        )

        try:
            # 1. Débiter la source
            source_wallet.debit(
                amount,
                description=f"Transfert vers {destination_user.email} - {txn.reference}"
            )
            logger.info(f"Transfer - Source debited: {amount}")

            # 2. Créditer la destination (NET après frais)
            destination_wallet.credit(
                amount_net,
                description=f"Transfert de {source_user.email} - {txn.reference}"
            )
            logger.info(f"Transfer - Destination credited: {amount_net}")

            # 3. Marquer comme COMPLETED
            txn.status = Transaction.Status.COMPLETED
            txn.completed_at = timezone.now()
            txn.save()

            # 4. Notifier les deux parties
            db_transaction.on_commit(lambda: WalletTransferService._notify_transfer(
                source_user, destination_user, amount, amount_net, fee_amount
            ))

            logger.info(f"Transfer completed - Transaction: {txn.reference}")
            return txn

        except Exception as e:
            txn.status = Transaction.Status.FAILED
            txn.failure_reason = str(e)
            txn.save()
            logger.error(f"Transfer failed - Transaction: {txn.reference}, Error: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _notify_transfer(source_user, destination_user, amount, amount_net, fee_amount):
        """
        Envoyer les notifications pour un transfert.
        """
        try:
            from apps.notifications.models import Notification

            # Notification pour l'expéditeur
            Notification.objects.create(
                recipient=source_user,
                notification_type='INFO',
                title=f"Transfert de {amount} FCFA",
                message=f"Vous avez transféré {amount} FCFA à {destination_user.email}. Frais: {fee_amount} FCFA.",
                data={
                    'amount': str(amount),
                    'amount_net': str(amount_net),
                    'fee': str(fee_amount),
                    'destination': destination_user.email,
                    'type': 'outgoing'
                }
            )

            # Notification pour le destinataire
            Notification.objects.create(
                recipient=destination_user,
                notification_type='SUCCESS',
                title=f"Réception de {amount_net} FCFA",
                message=f"Vous avez reçu {amount_net} FCFA de {source_user.email}.",
                data={
                    'amount': str(amount_net),
                    'source': source_user.email,
                    'type': 'incoming'
                }
            )

            logger.info(f"Notifications sent for transfer from {source_user.email} to {destination_user.email}")

        except Exception as e:
            logger.error(f"Failed to send notifications: {str(e)}", exc_info=True)

    @staticmethod
    @db_transaction.atomic
    def reverse_transaction(transaction_id: int, reason: str = "Annulation"):
        """
        Inverser une transaction (annulation).
        """
        try:
            transaction = Transaction.objects.get(id=transaction_id)
        except Transaction.DoesNotExist:
            raise ValidationError("Transaction non trouvée.")

        if transaction.status != Transaction.Status.COMPLETED:
            raise ValidationError("Seules les transactions terminées peuvent être inversées.")

        if transaction.transaction_type != Transaction.TransactionType.TRANSFER:
            raise ValidationError("Seules les transactions de transfert peuvent être inversées.")

        if not transaction.source_wallet or not transaction.destination_wallet:
            raise ValidationError("Les portefeuilles source ou destination sont manquants.")

        logger.info(f"Reversing transaction: {transaction.reference}")

        # Arrondir le montant
        amount = WalletTransferService._round_to_two_decimals(transaction.amount_net)

        # Créer la transaction inverse
        reverse_txn = Transaction.objects.create(
            wallet=transaction.destination_wallet,
            source_wallet=transaction.destination_wallet,
            destination_wallet=transaction.source_wallet,
            transaction_type=Transaction.TransactionType.REFUND,
            amount=amount,
            amount_net=amount,
            status=Transaction.Status.PENDING,
            description=f"Inversion de la transaction #{transaction.id} - {reason}",
            metadata={
                'reversed_transaction_id': transaction.id,
                'reason': reason,
                'original_transaction_reference': str(transaction.reference),
            }
        )

        try:
            # Débiter le wallet du destinataire original
            source_wallet = transaction.destination_wallet
            source_wallet.debit(
                amount,
                description=f"Annulation transfert - {reverse_txn.reference}"
            )

            # Créditer le wallet de l'expéditeur original
            dest_wallet = transaction.source_wallet
            dest_wallet.credit(
                amount,
                description=f"Annulation transfert - {reverse_txn.reference}"
            )

            # Marquer comme COMPLETED
            reverse_txn.status = Transaction.Status.COMPLETED
            reverse_txn.completed_at = timezone.now()
            reverse_txn.save()

            # Marquer la transaction originale comme REVERSED
            transaction.status = Transaction.Status.REVERSED
            transaction.save()

            logger.info(f"Transaction reversed: {transaction.reference}")
            return reverse_txn

        except Exception as e:
            reverse_txn.status = Transaction.Status.FAILED
            reverse_txn.failure_reason = str(e)
            reverse_txn.save()
            logger.error(f"Reverse failed: {str(e)}", exc_info=True)
            raise