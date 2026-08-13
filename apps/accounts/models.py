from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import CustomUserManager


class CustomUser(AbstractUser):
    """
    Modèle utilisateur personnalisé.
    Hérite de AbstractUser (qui fournit déjà password, is_active, is_staff, etc.)
    mais remplace username par email comme identifiant de connexion.
    """

    class Role(models.TextChoices):
        """
        TextChoices : façon moderne et propre de définir des choix en Django.
        Chaque rôle est stocké en base comme une courte chaîne (ex: 'SUPERADMIN'),
        et affiché de façon lisible dans l'admin (ex: 'Super Administrateur').
        """
        SUPERADMIN = 'SUPERADMIN', 'Super Administrateur'
        USERADMIN = 'USERADMIN', 'Administrateur'
        ENTREPRISE = 'ENTREPRISE', 'Entreprise'
        INVESTISSEUR = 'INVESTISSEUR', 'Investisseur'
        PLATFORM = 'PLATFORM', 'Compte Plateforme' 

    # On neutralise le champ username hérité d'AbstractUser (on ne l'utilise plus)
    username = None

    # Email devient le champ d'identification unique
    email = models.EmailField(
        unique=True,
        verbose_name="Adresse email",
        help_text="Utilisé comme identifiant de connexion."
    )

    # Champ métier : rôle RBAC (utilisé dès l'étape suivante)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.INVESTISSEUR,
        verbose_name="Rôle"
    )

    # Statut d'activation du compte (lié à l'activation par email, plus bas dans l'étape 2)
    is_email_verified = models.BooleanField(
        default=False,
        verbose_name="Email vérifié"
    )

    # Horodatage automatique de création du compte
    created_at = models.DateTimeField(auto_now_add=True)

    # Horodatage automatique de dernière modification
    updated_at = models.DateTimeField(auto_now=True)

    # Indique à Django d'utiliser 'email' pour l'authentification au lieu de 'username'
    USERNAME_FIELD = 'email'

    # Champs demandés en plus par `createsuperuser` (email et password sont déjà gérés automatiquement)
    REQUIRED_FIELDS = []

    # On branche notre manager personnalisé
    objects = CustomUserManager()

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['-created_at']

    def __str__(self):
        # Représentation lisible de l'objet, utilisée dans l'admin Django et les logs
        return f"{self.email} ({self.get_role_display()})"