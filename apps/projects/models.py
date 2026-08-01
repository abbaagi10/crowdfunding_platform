from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Category(models.Model):
    """
    Catégorie de projet (ex: Technologie, Santé, Environnement, Culture...).
    Modèle simple, géré par l'administration, réutilisé par tous les projets.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description")
    slug = models.SlugField(max_length=120, unique=True, blank=True, verbose_name="Slug")

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-génère le slug à partir du nom si non fourni (ex: "Santé & Bien-être" -> "sante-bien-etre")
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Project(models.Model):
    """
    Modèle central de la plateforme : une campagne de collecte de fonds
    portée par une entreprise (CompanyProfile).
    """

    class Status(models.TextChoices):
        """
        Cycle de vie d'un projet. Les transitions entre statuts sont
        contrôlées par la logique métier (voir permissions.py / views.py),
        pas seulement par ce champ.
        """
        DRAFT = 'DRAFT', 'Brouillon'
        PENDING = 'PENDING', 'En attente de validation'
        NEEDS_CORRECTION = 'NEEDS_CORRECTION', 'Corrections demandées'
        APPROVED = 'APPROVED', 'Approuvé'
        REJECTED = 'REJECTED', 'Refusé'
        ACTIVE = 'ACTIVE', 'Actif (collecte en cours)'
        COMPLETED = 'COMPLETED', 'Terminé'
        CANCELLED = 'CANCELLED', 'Annulé'

    # --- Relation avec l'entreprise porteuse ---
    # ForeignKey (pas OneToOne) : une entreprise peut porter PLUSIEURS projets.
    company = models.ForeignKey(
        'companies.CompanyProfile',
        on_delete=models.CASCADE,
        related_name='projects',
        verbose_name="Entreprise porteuse"
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,  # Empêche de supprimer une catégorie utilisée par des projets
        related_name='projects',
        verbose_name="Catégorie"
    )

    # --- Informations principales ---
    title = models.CharField(max_length=255, verbose_name="Titre du projet")
    slug = models.SlugField(max_length=280, unique=True, blank=True, verbose_name="Slug")
    short_description = models.CharField(
        max_length=300,
        verbose_name="Description courte",
        help_text="Résumé affiché dans les listes de projets (300 caractères max)."
    )
    full_description = models.TextField(verbose_name="Description complète")

    cover_image = models.ImageField(
        upload_to='projects/covers/',
        null=True, blank=True,
        verbose_name="Image de couverture"
    )

    # --- Objectifs financiers ---
    # DecimalField, jamais FloatField, pour l'argent : précision exacte garantie,
    # pas d'erreurs d'arrondi liées à la représentation binaire des flottants.
    # max_digits=12, decimal_places=2 -> jusqu'à 9 999 999 999,99 (largement suffisant)
    funding_goal = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'))],
        verbose_name="Objectif de financement"
    )

    # Montant actuellement collecté. Champ dénormalisé (recalculé/mis à jour
    # à chaque investissement dans l'étape future Investment), pour éviter
    # de recalculer une somme sur toutes les transactions à chaque affichage.
    current_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant collecté"
    )

    # --- Dates de la campagne ---
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(verbose_name="Date de fin")

    # --- Statut et workflow de validation ---
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Statut"
    )

    # Rempli par l'administration si status = NEEDS_CORRECTION ou REJECTED
    admin_feedback = models.TextField(
        blank=True,
        verbose_name="Retour de l'administration"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Projet"
        verbose_name_plural = "Projets"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            # Garantit l'unicité du slug même si deux projets ont le même titre
            while Project.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def clean(self):
        """
        Validation au niveau modèle (appelée par full_clean(), et donc par les
        serializers DRF qui utilisent ModelSerializer -- validation automatique).
        Règles métier qui ne peuvent pas être exprimées par de simples contraintes de champ.
        """
        errors = {}

        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                errors['end_date'] = "La date de fin doit être postérieure à la date de début."

        if self.funding_goal is not None and self.current_amount is not None:
            if self.current_amount > self.funding_goal:
                errors['current_amount'] = "Le montant collecté ne peut pas dépasser l'objectif."

        if errors:
            raise ValidationError(errors)

    @property
    def funding_percentage(self):
        """Pourcentage de l'objectif atteint, calculé à la volée (non stocké)."""
        if self.funding_goal == 0:
            return 0
        return round((self.current_amount / self.funding_goal) * 100, 2)

    @property
    def is_open_for_investment(self):
        """
        Un projet n'accepte des investissements que s'il est ACTIVE
        ET que sa date de fin n'est pas dépassée.
        Utilisé par le futur module Investment (Étape 8) pour bloquer
        un investissement sur un projet clos ou non encore approuvé.
        """
        return self.status == self.Status.ACTIVE and self.end_date >= timezone.now().date()
