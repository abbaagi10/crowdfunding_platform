from django.db import models
from django.conf import settings
from decimal import Decimal


class Investment(models.Model):
    """
    Investissement d'un investisseur dans un projet.
    """

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Actif'
        REFUNDED = 'REFUNDED', 'Remboursé'
        PARTIALLY_REFUNDED = 'PARTIALLY_REFUNDED', 'Partiellement remboursé'

    investor_profile = models.ForeignKey(
        'investors.InvestorProfile',
        on_delete=models.CASCADE,
        related_name='investments'
    )

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='investments'
    )

    transaction = models.OneToOneField(
        'transactions.Transaction',
        on_delete=models.CASCADE,
        related_name='investment'
    )

    amount = models.DecimalField(max_digits=14, decimal_places=2)
    amount_refunded = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def remaining_amount(self):
        return self.amount - self.amount_refunded

    def __str__(self):
        return f"{self.investor_profile.user.email} - {self.project.title} - {self.amount} FCFA"