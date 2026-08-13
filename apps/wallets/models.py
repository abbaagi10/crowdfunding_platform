from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Wallet(models.Model):
    """
    Portefeuille financier d'un utilisateur (Investisseur OU Entreprise).

    balance          : solde TOTAL réel de l'utilisateur.
    locked_balance    : partie du solde immobilisée (ex: fonds engagés dans un
                        investissement en attente, ou en cours de retrait).
    available_balance : NON stocké -- calculé (balance - locked_balance),
                         c'est le montant réellement utilisable immédiatement.

    Pourquoi séparer balance et locked_balance plutôt qu'un seul champ ?
    Parce qu'un utilisateur peut avoir de l'argent sur son compte qui n'est
    PAS disponible (ex: un investissement en cours de traitement). Sans cette
    distinction, on risquerait de permettre un double-usage des mêmes fonds.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet',
        verbose_name="Utilisateur"
    )

    # DecimalField OBLIGATOIRE pour tout montant d'argent -- JAMAIS FloatField.
    # Voir la section 3 (pourquoi DecimalField) pour la justification complète.
    balance = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Solde total"
    )

    locked_balance = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Solde bloqué"
    )

    currency = models.CharField(
        max_length=3,
        default='EUR',
        verbose_name="Devise",
        help_text="Code ISO 4217 (EUR, USD...). Une seule devise gérée pour l'instant."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Portefeuille"
        verbose_name_plural = "Portefeuilles"
        constraints = [
            models.CheckConstraint(
                condition=Q(balance__gte=0),
                name='wallet_balance_non_negative'
            ),
            models.CheckConstraint(
                condition=Q(locked_balance__gte=0),
                name='wallet_locked_balance_non_negative'
            ),
            models.CheckConstraint(
                condition=Q(locked_balance__lte=models.F('balance')),
                name='wallet_locked_balance_lte_balance'
            ),
        ]

    def __str__(self):
        return f"Portefeuille de {self.user.email} ({self.balance} {self.currency})"

    @property
    def available_balance(self) -> Decimal:
        """
        Solde réellement disponible = solde total - solde bloqué.
        Propriété calculée, JAMAIS stockée : elle ne peut donc jamais
        être désynchronisée du reste des données (pas de risque d'incohérence).
        """
        return self.balance - self.locked_balance

    def credit(self, amount, description=""):
        """
        Crédite le portefeuille (ajoute des fonds).
        Enregistre systématiquement un mouvement dans l'historique.
        """
        if amount <= 0:
            raise ValidationError("Le montant à créditer doit être positif.")

        self.balance += amount
        self.full_clean()  # Vérifie les contraintes AVANT de sauvegarder
        self.save()

        WalletHistory.objects.create(
            wallet=self,
            movement_type=WalletHistory.MovementType.CREDIT,
            amount=amount,
            balance_after=self.balance,
            description=description
        )

    def debit(self, amount, description=""):
        """
        Débite le portefeuille (retire des fonds du solde DISPONIBLE,
        pas du solde bloqué -- on ne peut jamais débiter des fonds
        déjà immobilisés directement).
        """
        if amount <= 0:
            raise ValidationError("Le montant à débiter doit être positif.")

        if amount > self.available_balance:
            raise ValidationError(
                f"Solde disponible insuffisant : {self.available_balance} {self.currency} disponible, "
                f"{amount} {self.currency} demandé."
            )

        self.balance -= amount
        self.full_clean()
        self.save()

        WalletHistory.objects.create(
            wallet=self,
            movement_type=WalletHistory.MovementType.DEBIT,
            amount=amount,
            balance_after=self.balance,
            description=description
        )

    def lock_funds(self, amount, description=""):
        """
        Bloque une partie du solde disponible (ex: le temps qu'un
        investissement soit confirmé). L'argent reste dans balance,
        mais devient indisponible via locked_balance.
        """
        if amount <= 0:
            raise ValidationError("Le montant à bloquer doit être positif.")

        if amount > self.available_balance:
            raise ValidationError("Solde disponible insuffisant pour bloquer ce montant.")

        self.locked_balance += amount
        self.full_clean()
        self.save()

        WalletHistory.objects.create(
            wallet=self,
            movement_type=WalletHistory.MovementType.LOCK,
            amount=amount,
            balance_after=self.balance,
            description=description
        )

    def unlock_funds(self, amount, description=""):
        """
        Débloque une partie du solde précédemment verrouillé
        (ex: investissement annulé, fonds relâchés).
        """
        if amount <= 0:
            raise ValidationError("Le montant à débloquer doit être positif.")

        if amount > self.locked_balance:
            raise ValidationError("Montant à débloquer supérieur au solde bloqué.")

        self.locked_balance -= amount
        self.full_clean()
        self.save()

        WalletHistory.objects.create(
            wallet=self,
            movement_type=WalletHistory.MovementType.UNLOCK,
            amount=amount,
            balance_after=self.balance,
            description=description
        )


class WalletHistory(models.Model):
    """
    Historique IMMUABLE des mouvements de portefeuille (ledger).

    Principe comptable fondamental : on n'UPDATE et ne DELETE jamais
    une ligne d'historique. On ne fait qu'AJOUTER de nouvelles lignes.
    C'est ce qui permet de reconstituer l'intégralité de l'historique
    financier d'un utilisateur à des fins d'audit ou de litige.
    """

    class MovementType(models.TextChoices):
        CREDIT = 'CREDIT', 'Crédit'
        DEBIT = 'DEBIT', 'Débit'
        LOCK = 'LOCK', 'Blocage de fonds'
        UNLOCK = 'UNLOCK', 'Déblocage de fonds'

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name="Portefeuille"
    )

    movement_type = models.CharField(
        max_length=10,
        choices=MovementType.choices,
        verbose_name="Type de mouvement"
    )

    amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name="Montant du mouvement"
    )

    # Solde total APRÈS ce mouvement -- permet de vérifier la cohérence
    # de l'historique a posteriori (chaque ligne doit s'enchaîner logiquement).
    balance_after = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name="Solde après mouvement"
    )

    description = models.CharField(max_length=255, blank=True, verbose_name="Description")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historique de portefeuille"
        verbose_name_plural = "Historiques de portefeuille"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()} de {self.amount} sur {self.wallet.user.email}"
