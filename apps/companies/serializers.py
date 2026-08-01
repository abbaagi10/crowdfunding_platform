from rest_framework import serializers
from .models import CompanyProfile


class CompanyProfileSerializer(serializers.ModelSerializer):
    """
    Serializer complet du profil entreprise.
    Utilisé pour la consultation ET la modification par le propriétaire.
    """

    is_kyb_complete = serializers.ReadOnlyField()
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = CompanyProfile
        fields = (
            'id', 'user', 'user_email',
            'company_name', 'registration_number', 'company_type', 'industry_sector', 'website',
            'legal_representative_name', 'legal_representative_position', 'legal_representative_phone',
            'address_line', 'city', 'postal_code', 'country',
            'iban', 'bic_swift', 'bank_name',
            'company_logo', 'registration_document', 'legal_representative_id_document',
            'verification_status', 'rejection_reason', 'is_kyb_complete',
            'created_at', 'updated_at',
        )
        # verification_status et rejection_reason restent réservés à l'administration,
        # exactement comme pour InvestorProfile (Étape 4).
        read_only_fields = ('user', 'verification_status', 'rejection_reason', 'created_at', 'updated_at')


class CompanyProfileAdminUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer réservé à l'administration, pour approuver/rejeter un dossier KYB.
    """

    class Meta:
        model = CompanyProfile
        fields = ('verification_status', 'rejection_reason')
