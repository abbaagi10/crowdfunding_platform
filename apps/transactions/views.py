# apps/transactions/views.py
import logging
from decimal import Decimal

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from drf_spectacular.utils import extend_schema

from apps.accounts.permissions import IsAdminOrSuperAdmin
from apps.projects.models import Project
from .models import Transaction
from .services import TransactionService, WalletTransferService, InsufficientFundsError
from .serializers import (
    TransactionSerializer,
    DepositRequestSerializer,
    WithdrawRequestSerializer,
    InvestRequestSerializer,
    TransferRequestSerializer,
)

logger = logging.getLogger(__name__)


class MyTransactionListView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/transactions/me/
    Historique des transactions de l'utilisateur connecte.
    """
    serializer_class = TransactionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        logger.info(f"MyTransactionListView - User: {user.email}")

        wallet = getattr(user, 'wallet', None)
        if wallet is None:
            logger.warning(f"MyTransactionListView - No wallet for user: {user.email}")
            return Transaction.objects.none()

        queryset = Transaction.objects.filter(
            models.Q(wallet=wallet) |
            models.Q(source_wallet=wallet) |
            models.Q(destination_wallet=wallet)
        ).select_related(
            'project',
            'source_wallet__user',
            'destination_wallet__user'
        ).distinct().order_by('-created_at')

        logger.info(f"MyTransactionListView - Found {queryset.count()} transactions")
        return queryset


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
        user = request.user
        logger.info(f"DepositView - User: {user.email}")

        wallet = getattr(user, 'wallet', None)
        if wallet is None:
            return Response(
                {"detail": "Aucun portefeuille associe a ce compte."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DepositRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            txn = TransactionService.deposit(
                wallet,
                serializer.validated_data['amount'],
                description=serializer.validated_data.get('description', '')
            )
            logger.info(f"DepositView - Transaction created: {txn.reference}")
            return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"DepositView - Error: {str(e)}", exc_info=True)
            return Response(
                {"detail": f"Une erreur est survenue: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
        user = request.user
        logger.info(f"WithdrawView - User: {user.email}")

        wallet = getattr(user, 'wallet', None)
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
            logger.info(f"WithdrawView - Transaction created: {txn.reference}")
            return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)

        except InsufficientFundsError as e:
            logger.warning(f"WithdrawView - Insufficient funds: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"WithdrawView - Error: {str(e)}", exc_info=True)
            return Response(
                {"detail": f"Une erreur est survenue: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
        user = request.user
        logger.info(f"InvestView - User: {user.email}")

        wallet = getattr(user, 'wallet', None)
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
            return Response(
                {"detail": "Projet introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            txn = TransactionService.invest(
                wallet,
                project,
                serializer.validated_data['amount']
            )
            logger.info(f"InvestView - Transaction created: {txn.reference}")
            return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)

        except InsufficientFundsError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except DjangoValidationError as e:
            message = e.messages[0] if hasattr(e, 'messages') else str(e)
            return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"InvestView - Error: {str(e)}", exc_info=True)
            return Response(
                {"detail": f"Une erreur est survenue: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    tags=['transactions'],
    request=TransferRequestSerializer,
    responses={201: TransactionSerializer}
)
class TransferView(APIView):
    """
    Endpoint POST /api/v1/transactions/transfer/
    Transfert de fonds entre utilisateurs (wallet-to-wallet).
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user = request.user
        logger.info("=" * 80)
        logger.info(f"TransferView - New request from user: {user.email}")
        logger.info(f"TransferView - Request data: {request.data}")
        logger.info("=" * 80)

        # Vérifier que l'utilisateur a un wallet
        if not hasattr(user, 'wallet'):
            logger.error(f"TransferView - No wallet for user: {user.email}")
            return Response(
                {"detail": "Vous n'avez pas de portefeuille."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Normaliser le montant avant validation
        amount_raw = request.data.get('amount')
        if amount_raw is None:
            return Response(
                {"detail": "Le montant est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Convertir le montant en Decimal avec 2 décimales
            if isinstance(amount_raw, str):
                amount_raw = amount_raw.replace(',', '.').strip()
            amount = Decimal(str(amount_raw)).quantize(Decimal('0.01'))

            if amount <= 0:
                return Response(
                    {"detail": "Le montant doit être supérieur à 0."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except (ValueError, TypeError, ArithmeticError) as e:
            logger.error(f"TransferView - Invalid amount: {amount_raw}, Error: {str(e)}")
            return Response(
                {"detail": "Le montant doit être un nombre valide."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Valider le serializer avec le montant normalisé
        serializer = TransferRequestSerializer(
            data={
                'email': request.data.get('email'),
                'amount': str(amount),  # Passer en chaîne pour éviter les problèmes de conversion
                'description': request.data.get('description', '')
            }
        )

        if not serializer.is_valid():
            logger.error(f"TransferView - Validation errors: {serializer.errors}")
            return Response(
                {"detail": "Données invalides", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data['email']
        description = serializer.validated_data.get('description', '')

        logger.info(f"TransferView - Validated: Email={email}, Amount={amount}, Description={description}")
        logger.info(f"TransferView - Source balance: {user.wallet.balance}")
        logger.info(f"TransferView - Source available: {user.wallet.available_balance}")

        # Vérifier que le destinataire existe
        try:
            destination_user = User.objects.get(email=email)

            if not hasattr(destination_user, 'wallet'):
                logger.error(f"TransferView - Destination has no wallet: {email}")
                return Response(
                    {"detail": f"L'utilisateur {email} n'a pas de portefeuille."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"TransferView - Destination found: {destination_user.email}")

        except User.DoesNotExist:
            logger.error(f"TransferView - Destination not found: {email}")
            return Response(
                {"detail": f"Utilisateur avec l'email {email} non trouvé."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Empêcher l'auto-transfert
        if destination_user == user:
            logger.error(f"TransferView - Self-transfer attempted")
            return Response(
                {"detail": "Vous ne pouvez pas vous transférer de l'argent à vous-même."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Effectuer le transfert
        try:
            logger.info(f"TransferView - Calling WalletTransferService.transfer()")
            transaction = WalletTransferService.transfer(
                source_user=user,
                destination_user=destination_user,
                amount=amount,
                description=description,
            )

            logger.info(f"TransferView - Transfer successful! Transaction: {transaction.reference}")
            return Response(
                TransactionSerializer(transaction).data,
                status=status.HTTP_201_CREATED
            )

        except InsufficientFundsError as e:
            logger.warning(f"TransferView - Insufficient funds: {str(e)}")
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except DjangoValidationError as e:
            message = e.messages[0] if hasattr(e, 'messages') else str(e)
            logger.warning(f"TransferView - Validation error: {message}")
            return Response(
                {"detail": message},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"TransferView - Unexpected error: {str(e)}", exc_info=True)
            return Response(
                {"detail": f"Une erreur est survenue lors du transfert: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TransactionListView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/transactions/
    Reserve a l'administration : vue d'audit de TOUTES les transactions.
    """
    queryset = Transaction.objects.all().select_related(
        'wallet__user',
        'project',
        'source_wallet__user',
        'destination_wallet__user'
    )
    serializer_class = TransactionSerializer
    permission_classes = (IsAdminOrSuperAdmin,)

    def get_queryset(self):
        logger.info(f"TransactionListView - Accessed by admin: {self.request.user.email}")
        return super().get_queryset()