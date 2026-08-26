# apps/transactions/serializers.py
from decimal import Decimal
from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer de CONSULTATION uniquement. Aucune transaction ne se cree
    directement via un serializer/vue generique -- toute creation passe
    exclusivement par TransactionService.
    """

    wallet_user_email = serializers.EmailField(
        source='wallet.user.email',
        read_only=True
    )
    project_title = serializers.CharField(
        source='project.title',
        read_only=True,
        default=None
    )
    source_user_email = serializers.EmailField(
        source='source_wallet.user.email',
        read_only=True
    )
    destination_user_email = serializers.EmailField(
        source='destination_wallet.user.email',
        read_only=True
    )

    class Meta:
        model = Transaction
        fields = (
            'id', 'reference', 'wallet', 'wallet_user_email',
            'source_wallet', 'destination_wallet',
            'source_user_email', 'destination_user_email',
            'transaction_type', 'amount', 'amount_net',
            'fee_amount', 'fee_rate', 'status',
            'project', 'project_title', 'description',
            'metadata', 'external_reference',
            'failure_reason', 'completed_at',
            'created_at', 'updated_at',
        )
        read_only_fields = fields


class DepositRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2,
        min_value=Decimal('0.01')
    )
    description = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True
    )


class WithdrawRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2,
        min_value=Decimal('0.01')
    )
    description = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True
    )


class InvestRequestSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2,
        min_value=Decimal('0.01')
    )


class TransferRequestSerializer(serializers.Serializer):
    """
    Serializer pour les requêtes de transfert.
    Accepte les montants sous différents formats (entier, flottant, chaîne).
    """
    email = serializers.EmailField(
        error_messages={
            'required': 'L\'email du destinataire est requis.',
            'invalid': 'Veuillez fournir une adresse email valide.'
        }
    )
    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal('0.01'),
        error_messages={
            'required': 'Le montant est requis.',
            'min_value': 'Le montant doit être supérieur à 0.',
            'invalid': 'Le montant doit être un nombre valide.'
        }
    )
    description = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    def validate_amount(self, value):
        """
        Valide et normalise le montant.
        """
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être positif.")
        
        # Arrondir à 2 décimales
        return value.quantize(Decimal('0.01'))


class TransferResponseSerializer(serializers.Serializer):
    """
    Serializer pour la réponse de transfert.
    """
    success = serializers.BooleanField()
    transaction = TransactionSerializer()
    message = serializers.CharField(required=False)