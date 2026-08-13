from decimal import Decimal

from django.db import models


class Investment(models.Model):
    """
    Represente la POSITION d'un investisseur dans un projet -- distinct
    d'une Transaction (qui est l'evenement financier instantane).

    Un Investment est cree AUTOMATIQUEMENT par TransactionService.invest()
    (Etape 8), jamais directement par une vue ou un serializer generique.
    Il decoule toujours d'une Transaction INVESTMENT reussie.

    Plusieurs Investment peuvent exister pour le meme couple
    (investisseur, projet) -- un investisseur peut renforcer sa position
    en investissant plusieurs fois dans le meme projet.
    """

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Actif'
        REFUNDED = 'REFUNDED', 'Rembourse'
        # PARTIALLY_REFUNDED sera utilise a l'Etape 10 (Repayment) lorsque
        # les remboursements partiels seront geres.
        PARTIALLY_REFUNDED = 'PARTIALLY_REFUNDED', 'Partiellement rembourse'

    investor_profile = models.ForeignKey(
        'investors.InvestorProfile',
        on_delete=models.PROTECT,  # Un investissement reste une preuve, meme si le profil est modifie
        related_name='investments',
        verbose_name="Profil investisseur"
    )

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.PROTECT,
        related_name='investments',
        verbose_name="Projet"
    )

    # Lien vers la Transaction qui a CREE cet investissement -- OneToOne
    # car une Transaction INVESTMENT correspond a EXACTEMENT un Investment,
    # jamais plusieurs, jamais zero (coherence garantie par le service).
    transaction = models.OneToOneField(
        'transactions.Transaction',
        on_delete=models.PROTECT,
        related_name='investment',
        verbose_name="Transaction d'origine"
    )

    amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name="Montant investi"
    )

    # Montant deja rembourse sur CET investissement precis (utilise a l'Etape 10).
    # Permet de savoir si un investissement est totalement, partiellement,
    # ou pas du tout rembourse, sans recalculer depuis Transaction a chaque fois.
    amount_refunded = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant deja rembourse"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Statut"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Investissement"
        verbose_name_plural = "Investissements"
        ordering = ['-created_at']
        indexes = [
            # Acceleration de la requete "tous les investissements de cet investisseur"
            models.Index(fields=['investor_profile', '-created_at']),
            # Acceleration de la requete "tous les investissements dans ce projet"
            models.Index(fields=['project', '-created_at']),
        ]

    def __str__(self):
        return f"{self.investor_profile.user.email} -> {self.project.title} : {self.amount}"

    @property
    def remaining_amount(self) -> Decimal:
        """Montant encore non rembourse sur cet investissement (utilise a l'Etape 10)."""
        return self.amount - self.amount_refunded
