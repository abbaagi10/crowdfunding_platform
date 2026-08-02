from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import CompanyProfile
from apps.projects.models import Category, Project
from apps.wallets.models import Wallet
from apps.transactions.models import Transaction
from apps.transactions.services import TransactionService

User = get_user_model()


class DepositViewTests(APITestCase):
    """
    Tests de l'endpoint /transactions/deposit/.
    """

    def setUp(self):
        self.deposit_url = reverse('transactions:deposit')
        self.investor = User.objects.create_user(
            email="tv_deposit@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.admin = User.objects.create_user(
            email="tv_deposit_admin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )

    def test_authenticated_investor_can_deposit(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.post(self.deposit_url, {"amount": "100.00"}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], Transaction.Status.COMPLETED)
        self.assertEqual(response.data['transaction_type'], Transaction.TransactionType.DEPOSIT)

    def test_unauthenticated_cannot_deposit(self):
        response = self.client.post(self.deposit_url, {"amount": "100.00"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_without_wallet_gets_404_on_deposit(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.deposit_url, {"amount": "100.00"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_negative_amount_rejected(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.post(self.deposit_url, {"amount": "-50.00"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zero_amount_rejected(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.post(self.deposit_url, {"amount": "0.00"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class WithdrawViewTests(APITestCase):
    """
    Tests de l'endpoint /transactions/withdraw/.
    """

    def setUp(self):
        self.withdraw_url = reverse('transactions:withdraw')
        self.investor = User.objects.create_user(
            email="tv_withdraw@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.wallet = Wallet.objects.get(user=self.investor)
        TransactionService.deposit(self.wallet, Decimal('200.00'))

    def test_withdraw_within_balance_succeeds(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.post(self.withdraw_url, {"amount": "50.00"}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['transaction_type'], Transaction.TransactionType.WITHDRAWAL)

    def test_withdraw_exceeding_balance_returns_400(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.post(self.withdraw_url, {"amount": "9999.00"}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("insuffisant", response.data['detail'])

    def test_wallet_balance_unchanged_after_failed_withdraw(self):
        self.client.force_authenticate(user=self.investor)
        self.client.post(self.withdraw_url, {"amount": "9999.00"}, format='json')

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('200.00'))


class InvestViewTests(APITestCase):
    """
    Tests de l'endpoint /transactions/invest/.
    """

    def setUp(self):
        self.invest_url = reverse('transactions:invest')

        self.investor = User.objects.create_user(
            email="tv_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.wallet = Wallet.objects.get(user=self.investor)
        TransactionService.deposit(self.wallet, Decimal('1000.00'))

        self.company_user = User.objects.create_user(
            email="tv_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="TV SAS", registration_number="FR999888000"
        )
        self.category = Category.objects.create(name="TV Category")

        self.project = Project.objects.create(
            company=self.company, category=self.category, title="Projet TV",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('500.00'),
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )

    def test_invest_in_active_project_succeeds(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.post(self.invest_url, {
            "project_id": self.project.id,
            "amount": "100.00"
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['project'], self.project.id)

    def test_invest_nonexistent_project_returns_404(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.post(self.invest_url, {
            "project_id": 999999,
            "amount": "100.00"
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invest_exceeding_goal_returns_400(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.post(self.invest_url, {
            "project_id": self.project.id,
            "amount": "600.00"
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_project_current_amount_unchanged_after_failed_investment(self):
        self.client.force_authenticate(user=self.investor)
        self.client.post(self.invest_url, {
            "project_id": self.project.id,
            "amount": "600.00"
        }, format='json')

        self.project.refresh_from_db()
        self.assertEqual(self.project.current_amount, Decimal('0.00'))


class MyTransactionListViewTests(APITestCase):
    """
    Tests de l'endpoint /transactions/me/.
    """

    def setUp(self):
        self.list_url = reverse('transactions:my_transactions')
        self.investor = User.objects.create_user(
            email="tv_mylist@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.other_investor = User.objects.create_user(
            email="tv_mylist_other@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.wallet = Wallet.objects.get(user=self.investor)
        self.other_wallet = Wallet.objects.get(user=self.other_investor)

        TransactionService.deposit(self.wallet, Decimal('100.00'))
        TransactionService.deposit(self.other_wallet, Decimal('200.00'))

    def test_user_sees_only_own_transactions(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['wallet_user_email'], "tv_mylist@example.com")


class TransactionListViewTests(APITestCase):
    """
    Tests de l'endpoint /transactions/ : audit reserve a l'administration.
    """

    def setUp(self):
        self.list_url = reverse('transactions:transaction_list')

        self.superadmin = User.objects.create_user(
            email="tv_audit_admin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )
        self.investor = User.objects.create_user(
            email="tv_audit_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.wallet = Wallet.objects.get(user=self.investor)
        TransactionService.deposit(self.wallet, Decimal('50.00'))

    def test_admin_can_list_all_transactions(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_investor_cannot_access_global_transaction_list(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
