from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import CompanyProfile
from apps.investors.models import InvestorProfile
from apps.projects.models import Category, Project
from apps.wallets.models import Wallet
from apps.transactions.services import TransactionService

User = get_user_model()


class MyInvestmentListViewTests(APITestCase):
    """
    Tests de l'endpoint /investments/me/.
    """

    def setUp(self):
        self.me_url = reverse('investments:my_investments')

        self.investor = User.objects.create_user(
            email="iv_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.investor_profile = InvestorProfile.objects.create(user=self.investor)
        self.wallet = Wallet.objects.get(user=self.investor)
        TransactionService.deposit(self.wallet, Decimal('500.00'))

        self.other_investor = User.objects.create_user(
            email="iv_other_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        InvestorProfile.objects.create(user=self.other_investor)
        self.other_wallet = Wallet.objects.get(user=self.other_investor)
        TransactionService.deposit(self.other_wallet, Decimal('500.00'))

        self.company_user = User.objects.create_user(
            email="iv_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="IV SAS", registration_number="FR444555666"
        )
        self.category = Category.objects.create(name="IV Category")
        self.project = Project.objects.create(
            company=self.company, category=self.category, title="Projet IV",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('1000.00'),
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )

    def test_investor_sees_only_own_investments(self):
        TransactionService.invest(self.wallet, self.project, Decimal('100.00'))
        TransactionService.invest(self.other_wallet, self.project, Decimal('200.00'))

        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['amount'], '100.00')

    def test_multiple_investments_in_same_project_all_visible(self):
        TransactionService.invest(self.wallet, self.project, Decimal('50.00'))
        TransactionService.invest(self.wallet, self.project, Decimal('30.00'))

        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.me_url)

        self.assertEqual(len(response.data), 2)

    def test_unauthenticated_cannot_access(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MyInvestmentSummaryViewTests(APITestCase):
    """
    Tests de l'endpoint /investments/me/summary/.
    """

    def setUp(self):
        self.summary_url = reverse('investments:my_investments_summary')

        self.investor = User.objects.create_user(
            email="is_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.investor_profile = InvestorProfile.objects.create(user=self.investor)
        self.wallet = Wallet.objects.get(user=self.investor)
        TransactionService.deposit(self.wallet, Decimal('500.00'))

        self.company_user = User.objects.create_user(
            email="is_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="IS SAS", registration_number="FR777888999"
        )
        self.category = Category.objects.create(name="IS Category")
        self.project1 = Project.objects.create(
            company=self.company, category=self.category, title="Projet IS 1",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('1000.00'),
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )
        self.project2 = Project.objects.create(
            company=self.company, category=self.category, title="Projet IS 2",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('1000.00'),
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )

    def test_summary_with_no_investments(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.summary_url)

        self.assertEqual(response.data['total_invested'], '0')
        self.assertEqual(response.data['projects_count'], 0)

    def test_summary_aggregates_multiple_investments_same_project(self):
        TransactionService.invest(self.wallet, self.project1, Decimal('50.00'))
        TransactionService.invest(self.wallet, self.project1, Decimal('30.00'))

        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.summary_url)

        self.assertEqual(response.data['total_invested'], '80.00')
        self.assertEqual(response.data['projects_count'], 1)

    def test_summary_counts_distinct_projects_correctly(self):
        TransactionService.invest(self.wallet, self.project1, Decimal('50.00'))
        TransactionService.invest(self.wallet, self.project2, Decimal('70.00'))

        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.summary_url)

        self.assertEqual(response.data['total_invested'], '120.00')
        self.assertEqual(response.data['projects_count'], 2)


class ProjectInvestmentListViewTests(APITestCase):
    """
    Tests de l'endpoint /investments/project/<id>/.
    """

    def setUp(self):
        self.investor = User.objects.create_user(
            email="pi_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        InvestorProfile.objects.create(user=self.investor)
        self.wallet = Wallet.objects.get(user=self.investor)
        TransactionService.deposit(self.wallet, Decimal('500.00'))

        self.owner_company_user = User.objects.create_user(
            email="pi_owner_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.owner_company = CompanyProfile.objects.create(
            user=self.owner_company_user, company_name="PI Owner SAS", registration_number="FR111222444"
        )

        self.other_company_user = User.objects.create_user(
            email="pi_other_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.other_company = CompanyProfile.objects.create(
            user=self.other_company_user, company_name="PI Other SAS", registration_number="FR555666777"
        )

        self.superadmin = User.objects.create_user(
            email="pi_superadmin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )

        self.category = Category.objects.create(name="PI Category")
        self.project = Project.objects.create(
            company=self.owner_company, category=self.category, title="Projet PI",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('1000.00'),
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )
        TransactionService.invest(self.wallet, self.project, Decimal('100.00'))

        self.project_url = reverse('investments:project_investments', kwargs={'project_id': self.project.id})

    def test_project_owner_company_sees_investments(self):
        self.client.force_authenticate(user=self.owner_company_user)
        response = self.client.get(self.project_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_other_company_sees_empty_list(self):
        """Une AUTRE entreprise ne doit voir AUCUN investissement de ce projet (liste vide, pas 403)."""
        self.client.force_authenticate(user=self.other_company_user)
        response = self.client.get(self.project_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_investor_sees_empty_list(self):
        """Un investisseur (non-admin, non-proprietaire) voit une liste vide, pas d'erreur."""
        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.project_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_admin_sees_all_investments(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get(self.project_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class InvestmentListViewTests(APITestCase):
    """
    Tests de l'endpoint /investments/ : audit global reserve a l'administration.
    """

    def setUp(self):
        self.list_url = reverse('investments:investment_list')

        self.investor = User.objects.create_user(
            email="il_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        InvestorProfile.objects.create(user=self.investor)
        self.wallet = Wallet.objects.get(user=self.investor)
        TransactionService.deposit(self.wallet, Decimal('500.00'))

        self.company_user = User.objects.create_user(
            email="il_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="IL SAS", registration_number="FR888999000"
        )
        self.category = Category.objects.create(name="IL Category")
        self.project = Project.objects.create(
            company=self.company, category=self.category, title="Projet IL",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('1000.00'),
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )
        TransactionService.invest(self.wallet, self.project, Decimal('100.00'))

        self.superadmin = User.objects.create_user(
            email="il_superadmin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )

    def test_admin_can_list_all_investments(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_investor_cannot_access_global_investment_list(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
