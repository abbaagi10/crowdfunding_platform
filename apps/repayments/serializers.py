from rest_framework import serializers
from .models import Repayment, RepaymentPlan


class RepaymentSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les échéances."""
    total_amount = serializers.ReadOnlyField()
    project_title = serializers.CharField(source='investment.project.title', read_only=True)
    investor_email = serializers.EmailField(source='investment.investor_profile.user.email', read_only=True)

    class Meta:
        model = Repayment
        fields = (
            'id', 'plan', 'investment',
            'installment_number', 'due_date',
            'capital_amount', 'interest_amount', 'total_amount',
            'status', 'paid_at',
            'project_title', 'investor_email',
            'created_at'
        )
        read_only_fields = ('id', 'created_at')


class RepaymentPlanSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les plans de remboursement."""
    total_amount = serializers.ReadOnlyField()
    repayments = RepaymentSerializer(many=True, read_only=True)
    project_title = serializers.CharField(source='project.title', read_only=True)

    class Meta:
        model = RepaymentPlan
        fields = (
            'id', 'project', 'project_title',
            'interest_rate', 'number_of_installments', 'frequency_days',
            'total_capital', 'total_interest', 'total_amount',
            'status', 'repayments',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class GeneratePlanSerializer(serializers.Serializer):
    """Sérialiseur pour la génération de plan."""
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    number_of_installments = serializers.IntegerField(min_value=1)
    frequency_days = serializers.IntegerField(min_value=1, default=30)