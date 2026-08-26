# apps/transactions/models.py
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Transaction(models.Model):
    """
    Journal UNIFIE de tout mouvement financier reel sur la plateforme.

    Une Transaction ne modifie JAMAIS directement balance/locked_balance --
    c'est le WalletHistory qui journalise le mouvement de solde.
    Transaction, elle, journalise l'EVENEMENT METIER complet (un depot,
    un investissement, un remboursement...), avec son contexte (projet lie,
    statut, reference), pas seulement le chiffre du mouvement.

    Distinction importante :
    - WalletHistory = "le solde de ce wallet a change de +100 le 02/08"
    - Transaction    = "Jean a investi 100E dans le Projet X, transaction #REF123,
                        actuellement en statut COMPLETED"
    """

    class TransactionType(models.TextChoices):
        DEPOSIT = 'DEPOSIT', 'Dépôt'
        WITHDRAWAL = 'WITHDRAWAL', 'Retrait'
        INVESTMENT = 'INVESTMENT', 'Investissement'
        REFUND = 'REFUND', 'Remboursement'
        INTEREST = 'INTEREST', 'Intérêt'
        COMMISSION = 'COMMISSION', 'Commission'
        TRANSFER = 'TRANSFER', 'Transfert'
        FEE = 'FEE', 'Frais'
        REBATE = 'REBATE', 'Ristourne'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        COMPLETED = 'COMPLETED', 'Terminée'
        FAILED = 'FAILED', 'Échouée'
        CANCELLED = 'CANCELLED', 'Annulée'
        REVERSED = 'REVERSED', 'Inversée'

    # Reference unique (UUID), utilisee pour la reconciliation comptable
    reference = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Reference"
    )

    # Champ legacy - gardé pour rétrocompatibilité
    wallet = models.ForeignKey(
        'wallets.Wallet',
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name="Portefeuille"
    )

    # Nouveaux champs pour wallet-to-wallet
    source_wallet = models.ForeignKey(
        'wallets.Wallet',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='outgoing_transactions',
        verbose_name="Portefeuille source"
    )

    destination_wallet = models.ForeignKey(
        'wallets.Wallet',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='incoming_transactions',
        verbose_name="Portefeuille destination"
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        verbose_name="Type de transaction"
    )

    amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant"
    )

    amount_net = models.DecimalField(
        max_digits=14, decimal_places=2,
        null=True, blank=True,
        verbose_name="Montant net (après frais)"
    )

    fee_amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Frais"
    )

    fee_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Taux de frais (%)"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut"
    )

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='transactions',
        verbose_name="Projet concerne"
    )

    description = models.CharField(
        max_length=255, blank=True,
        verbose_name="Description"
    )

    metadata = models.JSONField(
        default=dict, blank=True,
        verbose_name="Métadonnées"
    )

    external_reference = models.CharField(
        max_length=255, blank=True,
        verbose_name="Référence externe"
    )

    failure_reason = models.CharField(
        max_length=255, blank=True,
        verbose_name="Raison de l'echec"
    )

    completed_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Date de validation"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['source_wallet', '-created_at']),
            models.Index(fields=['destination_wallet', '-created_at']),
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} de {self.amount} ({self.get_status_display()}) - {self.reference}"