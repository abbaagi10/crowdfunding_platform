from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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
        wallet = Wallet.objects.filter(user=request.user).first()
        if wallet is None:
            # Cas normal pour un SUPERADMIN/USERADMIN : pas d'erreur serveur,
            # juste un message clair indiquant qu'il n'a pas de portefeuille.
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
        wallet = Wallet.objects.filter(user=self.request.user).first()
        if wallet is None:
            return WalletHistorySerializer.Meta.model.objects.none()
        return wallet.history.all()
