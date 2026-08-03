from rest_framework import serializers
from .models import RepaymentPlan, Repayment


class RepaymentPlanSerializer(serializers.ModelSerializer):
    total_amount = serializers.ReadOnlyField()
    project_title = serializers.CharField(source='project.title', read_only=True)

    class Meta:
        model = RepaymentPlan
        fields = (
            'id', 'project', 'project_title', 'interest_rate',
            'number_of_installments', 'frequency_days',
            'total_capital', 'total_interest', 'total_amount',
            'status', 'created_at', 'updated_at',
        )
        read_only_fields = fields


class GeneratePlanRequestSerializer(serializers.Serializer):
    """Valide les parametres d'entree pour generer un plan -- ne cree rien directement."""
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0)
    number_of_installments = serializers.IntegerField(min_value=1)
    frequency_days = serializers.IntegerField(min_value=1, default=30)


class RepaymentSerializer(serializers.ModelSerializer):
    """Serializer de CONSULTATION uniquement."""

    total_amount = serializers.ReadOnlyField()
    investor_email = serializers.EmailField(source='investment.investor_profile.user.email', read_only=True)
    project_title = serializers.CharField(source='plan.project.title', read_only=True)

    class Meta:
        model = Repayment
        fields = (
            'id', 'plan', 'investment', 'investor_email', 'project_title',
            'installment_number', 'due_date',
            'capital_amount', 'interest_amount', 'total_amount',
            'status', 'paid_at', 'created_at',
        )
        read_only_fields = fields
