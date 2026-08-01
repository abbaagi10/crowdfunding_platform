from django.core.validators import RegexValidator
from django.db import models
from django.conf import settings


class CompanyProfile(models.Model):
    """
    Profil complémentaire pour les utilisateurs ayant le rôle ENTREPRISE.
    Contient les informations KYB (Know Your Business) et bancaires
    nécessaires pour lever des fonds sur la plateforme.
    """

    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'En attente de vérification'
        APPROVED = 'APPROVED', 'Vérifié'
        REJECTED = 'REJECTED', 'Rejeté'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company_profile',
        verbose_name="Utilisateur"
    )

    # --- Informations légales de l'entreprise ---
    company_name = models.CharField(
        max_length=255,
        verbose_name="Raison sociale"
    )

    # unique=True : deux entreprises ne peuvent pas partager le même numéro d'enregistrement
    # (équivalent SIRET en France, ou tout numéro d'immatriculation légal)
    registration_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro d'enregistrement légal"
    )

    company_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Forme juridique",
        help_text="Ex: SARL, SAS, SA..."
    )

    industry_sector = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Secteur d'activité"
    )

    website = models.URLField(blank=True, verbose_name="Site web")

    # --- Représentant légal ---
    legal_representative_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nom du représentant légal"
    )

    legal_representative_position = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Fonction du représentant légal"
    )

    legal_representative_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Téléphone du représentant légal"
    )

    # --- Adresse du siège social ---
    address_line = models.CharField(max_length=255, blank=True, verbose_name="Adresse")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    postal_code = models.CharField(max_length=20, blank=True, verbose_name="Code postal")
    country = models.CharField(max_length=100, blank=True, verbose_name="Pays")

    # --- Compte bancaire (champs plats, voir justification architecturale ci-dessus) ---
    # RegexValidator : validation basique du format IBAN (lettres + chiffres, 15 à 34 caractères)
    # Ce n'est pas une validation de checksum IBAN complète, seulement un contrôle de format simple.
    iban = models.CharField(
        max_length=34,
        blank=True,
        validators=[RegexValidator(
            regex=r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$',
            message="Format IBAN invalide."
        )],
        verbose_name="IBAN"
    )

    bic_swift = models.CharField(max_length=11, blank=True, verbose_name="Code BIC/SWIFT")
    bank_name = models.CharField(max_length=255, blank=True, verbose_name="Nom de la banque")

    # --- Documents KYB ---
    company_logo = models.ImageField(
        upload_to='companies/logos/',
        null=True, blank=True,
        verbose_name="Logo de l'entreprise"
    )

    registration_document = models.FileField(
        upload_to='companies/documents/registration/',
        null=True, blank=True,
        verbose_name="Extrait d'immatriculation (Kbis ou équivalent)"
    )

    legal_representative_id_document = models.FileField(
        upload_to='companies/documents/representative_id/',
        null=True, blank=True,
        verbose_name="Pièce d'identité du représentant légal"
    )

    # --- Statut de vérification KYB ---
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        verbose_name="Statut de vérification"
    )

    rejection_reason = models.TextField(blank=True, verbose_name="Motif de rejet")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil Entreprise"
        verbose_name_plural = "Profils Entreprises"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company_name} ({self.get_verification_status_display()})"

    @property
    def is_kyb_complete(self):
        """
        Vérifie si les documents essentiels du dossier KYB ont été fournis.
        Utilisé dans l'étape future (module Projet) pour bloquer la création
        d'un projet de collecte tant que l'entreprise n'est pas vérifiée.
        """
        return bool(
            self.registration_document and
            self.legal_representative_id_document and
            self.legal_representative_name and
            self.iban
        )