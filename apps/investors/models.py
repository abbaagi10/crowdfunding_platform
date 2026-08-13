from django.db import models
from django.conf import settings


class InvestorProfile(models.Model):
    """
    Profil complémentaire pour les utilisateurs ayant le rôle INVESTISSEUR.
    Contient les informations KYC (Know Your Customer) nécessaires
    pour la conformité réglementaire d'une plateforme de crowdfunding.
    """

    class VerificationStatus(models.TextChoices):
        """Statut de vérification du dossier KYC par l'équipe d'administration."""
        PENDING = 'PENDING', 'En attente de vérification'
        APPROVED = 'APPROVED', 'Vérifié'
        REJECTED = 'REJECTED', 'Rejeté'

    # Relation OneToOne : chaque utilisateur a AU PLUS un profil investisseur.
    # on_delete=CASCADE : si le CustomUser est supprimé, son profil l'est aussi (cohérence des données).
    # related_name permet d'écrire user.investor_profile plutôt que user.investorprofile (moins lisible).
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='investor_profile',
        verbose_name="Utilisateur"
    )

    # --- Informations personnelles KYC ---
    date_of_birth = models.DateField(
        null=True, blank=True,
        verbose_name="Date de naissance"
    )

    nationality = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nationalité"
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Numéro de téléphone"
    )

    # --- Adresse ---
    address_line = models.CharField(max_length=255, blank=True, verbose_name="Adresse")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    postal_code = models.CharField(max_length=20, blank=True, verbose_name="Code postal")
    country = models.CharField(max_length=100, blank=True, verbose_name="Pays")

    # --- Documents et photo ---
    # upload_to définit le sous-dossier dans MEDIA_ROOT où le fichier sera stocké.
    # La fonction (plutôt qu'une chaîne fixe) permet d'organiser les fichiers par utilisateur.
    profile_photo = models.ImageField(
        upload_to='investors/photos/',
        null=True, blank=True,
        verbose_name="Photo de profil"
    )

    identity_document = models.FileField(
        upload_to='investors/documents/identity/',
        null=True, blank=True,
        verbose_name="Pièce d'identité"
    )

    proof_of_address = models.FileField(
        upload_to='investors/documents/address/',
        null=True, blank=True,
        verbose_name="Justificatif de domicile"
    )

    # --- Statut de vérification KYC ---
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        verbose_name="Statut de vérification"
    )

    # Raison du rejet, remplie par l'admin si verification_status = REJECTED
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="Motif de rejet"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil Investisseur"
        verbose_name_plural = "Profils Investisseurs"
        ordering = ['-created_at']

    def __str__(self):
        return f"Profil de {self.user.email} ({self.get_verification_status_display()})"

    @property
    def is_kyc_complete(self) -> bool:
        """
        Propriété calculée (pas stockée en base) qui vérifie si les documents
        essentiels ont été fournis. Utile pour bloquer un investissement
        tant que le KYC n'est pas complet (étape future : module Investment).
        """
        return bool(
            self.identity_document and
            self.proof_of_address and
            self.nationality and
            self.phone_number
        )