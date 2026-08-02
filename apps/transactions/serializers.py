from decimal import Decimal

from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    wallet_user_email = serializers.EmailField(source='wallet.user.email', read_only=True)
    project_title = serializers.CharField(source='project.title', read_only=True, default=None)

    class Meta:
        model = Transaction
        fields = (
            'id', 'reference', 'wallet', 'wallet_user_email',
            'transaction_type', 'amount', 'status',
            'project', 'project_title', 'description', 'failure_reason',
            'created_at', 'updated_at',
        )
        read_only_fields = fields


class DepositRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)


class WithdrawRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)


class InvestRequestSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))
