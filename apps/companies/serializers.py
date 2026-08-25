from rest_framework import serializers
from .models import CompanyProfile


class CompanyProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = CompanyProfile
        fields = [
            'id', 'user', 'user_email',
            'company_name', 'registration_number', 'company_type',
            'industry_sector', 'website',
            'legal_representative_name', 'legal_representative_position',
            'legal_representative_phone',
            'address_line', 'city', 'postal_code', 'country',
            'iban', 'bic_swift', 'bank_name',
            'company_logo', 'registration_document',
            'legal_representative_id_document',
            'verification_status', 'rejection_reason',
            'is_kyb_complete', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'user_email',
            'verification_status', 'rejection_reason',
            'is_kyb_complete', 'created_at', 'updated_at'
        ]


class CompanyProfileAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyProfile
        fields = ['verification_status', 'rejection_reason']