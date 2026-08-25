from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema

from apps.accounts.permissions import IsAdminOrSuperAdmin
from apps.projects.models import Project
from .models import Transaction
from .services import TransactionService, InsufficientFundsError
from .serializers import (
    TransactionSerializer,
    DepositRequestSerializer,
    WithdrawRequestSerializer,
    InvestRequestSerializer,
)


class MyTransactionListView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/transactions/me/
    Historique des transactions de l'utilisateur connecte.
    """
    serializer_class = TransactionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        wallet = getattr(self.request.user, 'wallet', None)
        if wallet is None:
            return Transaction.objects.none()
        return Transaction.objects.filter(wallet=wallet).select_related('project')


@extend_schema(
    tags=['transactions'],
    request=DepositRequestSerializer,
    responses={201: TransactionSerializer}
)
class DepositView(APIView):
    """
    Endpoint POST /api/v1/transactions/deposit/
    Simule un depot de fonds sur le wallet de l'utilisateur connecte.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        wallet = getattr(request.user, 'wallet', None)
        if wallet is None:
            return Response(
                {"detail": "Aucun portefeuille associe a ce compte."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DepositRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        txn = TransactionService.deposit(
            wallet,
            serializer.validated_data['amount'],
            description=serializer.validated_data.get('description', '')
        )

        return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['transactions'],
    request=WithdrawRequestSerializer,
    responses={201: TransactionSerializer}
)
class WithdrawView(APIView):
    """
    Endpoint POST /api/v1/transactions/withdraw/
    Simule un retrait de fonds depuis le wallet de l'utilisateur connecte.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        wallet = getattr(request.user, 'wallet', None)
        if wallet is None:
            return Response(
                {"detail": "Aucun portefeuille associe a ce compte."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = WithdrawRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            txn = TransactionService.withdraw(
                wallet,
                serializer.validated_data['amount'],
                description=serializer.validated_data.get('description', '')
            )
        except InsufficientFundsError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['transactions'],
    request=InvestRequestSerializer,
    responses={201: TransactionSerializer}
)
class InvestView(APIView):
    """
    Endpoint POST /api/v1/transactions/invest/
    Un investisseur investit dans un projet.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        wallet = getattr(request.user, 'wallet', None)
        if wallet is None:
            return Response(
                {"detail": "Aucun portefeuille associe a ce compte."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = InvestRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            project = Project.objects.get(pk=serializer.validated_data['project_id'])
        except Project.DoesNotExist:
            return Response({"detail": "Projet introuvable."}, status=status.HTTP_404_NOT_FOUND)

        try:
            txn = TransactionService.invest(wallet, project, serializer.validated_data['amount'])
        except InsufficientFundsError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoValidationError as e:
            message = e.messages[0] if hasattr(e, 'messages') else str(e)
            return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


class TransactionListView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/transactions/
    Reserve a l'administration : vue d'audit de TOUTES les transactions.
    """
    queryset = Transaction.objects.all().select_related('wallet__user', 'project')
    serializer_class = TransactionSerializer
    permission_classes = (IsAdminOrSuperAdmin,)