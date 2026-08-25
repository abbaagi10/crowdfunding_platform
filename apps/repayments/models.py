from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from decimal import Decimal


class RepaymentPlan(models.Model):
    """
    Plan de remboursement d'un projet.
    """

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Brouillon'
        ACTIVE = 'ACTIVE', 'Actif'
        COMPLETED = 'COMPLETED', 'Terminé'
        DEFAULTED = 'DEFAULTED', 'En défaut'

    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='repayment_plan'
    )

    interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Taux d'intérêt annuel (%)"
    )

    number_of_installments = models.PositiveIntegerField()
    frequency_days = models.PositiveIntegerField(default=30)

    total_capital = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal('0.00')
    )
    total_interest = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal('0.00')
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_amount(self):
        return self.total_capital + self.total_interest

    def __str__(self):
        return f"Plan de {self.project.title}"

    class Meta:
        verbose_name = "Plan de remboursement"
        verbose_name_plural = "Plans de remboursement"


class Repayment(models.Model):
    """
    Échéance individuelle de remboursement.
    """

    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Planifiée'
        PAID = 'PAID', 'Payée'
        LATE = 'LATE', 'En retard'
        CANCELLED = 'CANCELLED', 'Annulée'

    plan = models.ForeignKey(
        RepaymentPlan,
        on_delete=models.CASCADE,
        related_name='repayments'
    )

    investment = models.ForeignKey(
        'investments.Investment',
        on_delete=models.CASCADE,
        related_name='repayments'
    )

    installment_number = models.PositiveIntegerField()
    due_date = models.DateField()

    capital_amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal('0.00')
    )
    interest_amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal('0.00')
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )

    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_amount(self):
        return self.capital_amount + self.interest_amount

    def mark_as_paid(self):
        """Marquer l'échéance comme payée."""
        if self.status == self.Status.PAID:
            return

        from django.utils import timezone
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Échéance #{self.installment_number} - {self.investment.project.title}"

    class Meta:
        verbose_name = "Échéance"
        verbose_name_plural = "Échéances"
        ordering = ['due_date']