from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsAdminOrSuperAdmin
from .models import Wallet
from .serializers import WalletSerializer, WalletHistorySerializer


class MyWalletView(generics.RetrieveAPIView):
    """
    Endpoint GET /api/v1/wallets/wallet/me/
    Consultation du PROPRE portefeuille de l'utilisateur connecté.
    """
    serializer_class = WalletSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        # 🔒 Vérifier que l'utilisateur n'est pas un administrateur
        if request.user.role in ['SUPERADMIN', 'USERADMIN']:
            return Response(
                {"detail": "Les administrateurs n'ont pas de portefeuille."},
                status=status.HTTP_403_FORBIDDEN
            )

        wallet = Wallet.objects.filter(user=request.user).first()
        if wallet is None:
            return Response(
                {"detail": "Aucun portefeuille associé à ce compte (réservé aux investisseurs et entreprises)."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(wallet)
        return Response(serializer.data)


class MyWalletHistoryView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/wallets/wallet/me/history/
    Historique complet des mouvements du portefeuille de l'utilisateur connecté.
    """
    serializer_class = WalletHistorySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        # 🔒 Vérifier que l'utilisateur n'est pas un administrateur
        if self.request.user.role in ['SUPERADMIN', 'USERADMIN']:
            return Wallet.objects.none()

        wallet = Wallet.objects.filter(user=self.request.user).first()
        if wallet is None:
            return Wallet.objects.none()
        return wallet.history.all()


class WalletListView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/wallets/wallets/
    Reserve a l'administration : liste TOUS les portefeuilles, pour l'audit.
    STRICTEMENT en lecture -- aucune methode d'ecriture n'est exposee ici,
    volontairement (voir justification dans la documentation de l'etape).
    """
    queryset = Wallet.objects.all().select_related('user').order_by('-updated_at')
    serializer_class = WalletSerializer
    permission_classes = (IsAdminOrSuperAdmin,)


class WalletDetailView(generics.RetrieveAPIView):
    """
    Endpoint GET /api/v1/wallets/wallets/<id>/
    Reserve a l'administration : consultation d'UN portefeuille precis.
    RetrieveAPIView expose UNIQUEMENT le GET -- aucun risque de modification
    accidentelle via cette vue (pas de mixin update/destroy).
    """
    queryset = Wallet.objects.all().select_related('user')
    serializer_class = WalletSerializer
    permission_classes = (IsAdminOrSuperAdmin,)


class WalletHistoryDetailView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/wallets/wallets/<id>/history/
    Reserve a l'administration : historique complet d'UN portefeuille precis,
    pour l'audit d'un utilisateur en particulier (ex: en cas de litige).
    """
    serializer_class = WalletHistorySerializer
    permission_classes = (IsAdminOrSuperAdmin,)

    def get_queryset(self):
        wallet_id = self.kwargs['pk']
        wallet = Wallet.objects.filter(pk=wallet_id).first()
        if wallet is None:
            return Wallet.objects.none()
        return wallet.history.all()