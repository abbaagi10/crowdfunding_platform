from rest_framework import serializers
from .models import Wallet, WalletHistory


class WalletHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletHistory
        fields = ('id', 'movement_type', 'amount', 'balance_after', 'description', 'created_at')
        # TOUS les champs sont read_only : un mouvement ne se crée JAMAIS
        # directement via l'API, uniquement via les actions métier
        # (credit/debit/lock/unlock, exposées par des vues dédiées, pas ce serializer).
        read_only_fields = fields


class WalletSerializer(serializers.ModelSerializer):
    """
    Serializer de consultation du portefeuille.
    ENTIÈREMENT en lecture seule : aucun champ financier ne doit être
    modifiable directement par une requête utilisateur. Toute opération
    sur le solde passe par des ENDPOINTS D'ACTION dédiés (credit/debit/...),
    jamais par un PATCH générique sur le wallet lui-même.
    """

    available_balance = serializers.ReadOnlyField()
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Wallet
        fields = (
            'id', 'user', 'user_email',
            'balance', 'locked_balance', 'available_balance',
            'currency', 'created_at', 'updated_at',
        )
        read_only_fields = fields
