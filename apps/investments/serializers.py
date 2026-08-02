from rest_framework import serializers
from .models import Investment


class InvestmentSerializer(serializers.ModelSerializer):
    """
    Serializer de CONSULTATION uniquement -- un Investment ne se cree
    jamais directement via l'API, toujours via TransactionService.invest().
    """

    project_title = serializers.CharField(source='project.title', read_only=True)
    project_status = serializers.CharField(source='project.status', read_only=True)
    company_name = serializers.CharField(source='project.company.company_name', read_only=True)
    investor_email = serializers.EmailField(source='investor_profile.user.email', read_only=True)
    remaining_amount = serializers.ReadOnlyField()
    transaction_reference = serializers.UUIDField(source='transaction.reference', read_only=True)

    class Meta:
        model = Investment
        fields = (
            'id', 'investor_profile', 'investor_email',
            'project', 'project_title', 'project_status', 'company_name',
            'transaction', 'transaction_reference',
            'amount', 'amount_refunded', 'remaining_amount',
            'status', 'created_at', 'updated_at',
        )
        read_only_fields = fields
