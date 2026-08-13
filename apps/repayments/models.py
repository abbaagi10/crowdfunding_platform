from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class RepaymentPlan(models.Model):
    """
    Plan de remboursement GLOBAL pour un Project.
    Un seul RepaymentPlan par projet (OneToOne) -- definit les regles
    (taux, duree, frequence) a partir desquelles les echeances individuelles
    (Repayment) seront generees pour CHAQUE investisseur.
    """

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Brouillon'
        ACTIVE = 'ACTIVE', 'Actif'
        COMPLETED = 'COMPLETED', 'Termine'
        DEFAULTED = 'DEFAULTED', 'En defaut'

    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.PROTECT,
        related_name='repayment_plan',
        verbose_name="Projet"
    )

    # Taux d'interet ANNUEL, en pourcentage (ex: 5.00 pour 5%)
    interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name="Taux d'interet annuel (%)"
    )

    number_of_installments = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Nombre d'echeances"
    )

    # Frequence entre deux echeances, en jours (30 = mensuel, 90 = trimestriel...)
    frequency_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Frequence entre echeances (jours)"
    )

    # Capital total a rembourser = montant total collecte (project.current_amount
    # au moment de la generation du plan, fige pour ne pas varier si current_amount
    # change ensuite pour une raison quelconque).
    total_capital = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name="Capital total a rembourser"
    )

    # Total des interets sur toute la duree du plan (calcule a la generation)
    total_interest = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name="Total des interets"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Statut"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plan de remboursement"
        verbose_name_plural = "Plans de remboursement"

    def __str__(self):
        return f"Plan de {self.project.title} ({self.get_status_display()})"

    @property
    def total_amount(self) -> Decimal:
        """Montant total a rembourser, capital + interets confondus."""
        return self.total_capital + self.total_interest


class Repayment(models.Model):
    """
    UNE echeance de remboursement, POUR UN investissement precis.

    Si un projet a 3 investisseurs et un plan sur 12 echeances,
    on aura 3 x 12 = 36 lignes Repayment au total -- une par
    (investisseur, numero d'echeance).
    """

    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Planifiee'
        PAID = 'PAID', 'Payee'
        LATE = 'LATE', 'En retard'
        CANCELLED = 'CANCELLED', 'Annulee'

    plan = models.ForeignKey(
        RepaymentPlan,
        on_delete=models.CASCADE,  # Si le plan est supprime (jamais en prod normale), ses echeances aussi
        related_name='repayments',
        verbose_name="Plan de remboursement"
    )

    investment = models.ForeignKey(
        'investments.Investment',
        on_delete=models.PROTECT,  # Preuve financiere -- ne disparait jamais
        related_name='repayments',
        verbose_name="Investissement concerne"
    )

    installment_number = models.PositiveIntegerField(verbose_name="Numero d'echeance")

    due_date = models.DateField(verbose_name="Date d'exigibilite")

    # Part de CAPITAL de cette echeance, pour CET investisseur precis
    capital_amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name="Part de capital"
    )

    # Part d'INTERETS de cette echeance, pour CET investisseur precis
    interest_amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name="Part d'interets"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        verbose_name="Statut"
    )

    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Date de paiement effectif")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Echeance de remboursement"
        verbose_name_plural = "Echeances de remboursement"
        ordering = ['due_date', 'installment_number']
        indexes = [
            models.Index(fields=['investment', 'installment_number']),
            models.Index(fields=['status', 'due_date']),
        ]

    def __str__(self):
        return (
            f"Echeance #{self.installment_number} - {self.investment.investor_profile.user.email} "
            f"- {self.total_amount} ({self.get_status_display()})"
        )

    @property
    def total_amount(self) -> Decimal:
        """Montant total de CETTE echeance (capital + interets), pour CET investisseur."""
        return self.capital_amount + self.interest_amount
