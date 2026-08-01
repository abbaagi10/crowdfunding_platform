from rest_framework import serializers
from .models import InvestorProfile


class InvestorProfileSerializer(serializers.ModelSerializer):
    """
    Serializer complet du profil investisseur.
    Utilisé pour la consultation ET la modification par le propriétaire.
    """

    # Champs en lecture seule : dérivés, l'utilisateur ne doit jamais pouvoir les modifier directement
    is_kyc_complete = serializers.ReadOnlyField()
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = InvestorProfile
        fields = (
            'id', 'user', 'user_email',
            'date_of_birth', 'nationality', 'phone_number',
            'address_line', 'city', 'postal_code', 'country',
            'profile_photo', 'identity_document', 'proof_of_address',
            'verification_status', 'rejection_reason', 'is_kyc_complete',
            'created_at', 'updated_at',
        )
        # Un utilisateur normal ne doit JAMAIS pouvoir changer son propre statut de vérification
        # ni son motif de rejet -- ces champs sont réservés à l'administration (via une autre vue/action)
        read_only_fields = ('user', 'verification_status', 'rejection_reason', 'created_at', 'updated_at')


class InvestorProfileAdminUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer réservé à l'administration, pour approuver/rejeter un dossier KYC.
    Sépare volontairement ces champs sensibles du serializer "grand public" ci-dessus.
    """

    class Meta:
        model = InvestorProfile
        fields = ('verification_status', 'rejection_reason')