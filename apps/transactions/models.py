import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Transaction(models.Model):
    """
    Journal UNIFIE de tout mouvement financier reel sur la plateforme.

    Une Transaction ne modifie JAMAIS directement balance/locked_balance --
    c'est le WalletHistory (Etape 7) qui journalise le mouvement de solde.
    Transaction, elle, journalise l'EVENEMENT METIER complet (un depot,
    un investissement, un remboursement...), avec son contexte (projet lie,
    statut, reference), pas seulement le chiffre du mouvement.
    """

    class TransactionType(models.TextChoices):
        DEPOSIT = 'DEPOSIT', 'Depot'
        WITHDRAWAL = 'WITHDRAWAL', 'Retrait'
        INVESTMENT = 'INVESTMENT', 'Investissement'
        REFUND = 'REFUND', 'Remboursement'
        INTEREST = 'INTEREST', 'Interet'
        COMMISSION = 'COMMISSION', 'Commission'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        COMPLETED = 'COMPLETED', 'Terminee'
        FAILED = 'FAILED', 'Echouee'
        CANCELLED = 'CANCELLED', 'Annulee'

    reference = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Reference"
    )

    wallet = models.ForeignKey(
        'wallets.Wallet',
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name="Portefeuille"
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

    description = models.CharField(max_length=255, blank=True, verbose_name="Description")
    failure_reason = models.CharField(max_length=255, blank=True, verbose_name="Raison de l'echec")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} de {self.amount} ({self.get_status_display()}) - {self.reference}"