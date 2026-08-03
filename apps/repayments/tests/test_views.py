from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import CompanyProfile
from apps.investors.models import InvestorProfile
from apps.projects.models import Category, Project
from apps.wallets.models import Wallet
from apps.transactions.services import TransactionService
from apps.repayments.models import Repayment
from apps.repayments.services import RepaymentService
from django.utils import timezone

User = get_user_model()


class GeneratePlanViewTests(APITestCase):
    """
    Tests de l'endpoint /repayments/plans/generate/<project_id>/.
    """

    def setUp(self):
        self.superadmin = User.objects.create_user(
            email="gpv_superadmin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )
        self.company_user = User.objects.create_user(
            email="gpv_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="GPV SAS", registration_number="FR100100200"
        )
        self.category = Category.objects.create(name="GPV Category")
        self.project = Project.objects.create(
            company=self.company, category=self.category, title="GPV Project",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('1000.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )

        self.investor = User.objects.create_user(
            email="gpv_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        InvestorProfile.objects.create(user=self.investor)
        wallet = Wallet.objects.get(user=self.investor)
        TransactionService.deposit(wallet, Decimal('500.00'))
        wallet.refresh_from_db()
        TransactionService.invest(wallet, self.project, Decimal('500.00'))
        self.project.refresh_from_db()

        self.generate_url = reverse('repayments:generate_plan', kwargs={'project_id': self.project.id})

    def test_admin_can_generate_plan(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.post(self.generate_url, {
            "interest_rate": "10.00",
            "number_of_installments": 12,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total_capital'], '500.00')

    def test_non_admin_cannot_generate_plan(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.post(self.generate_url, {
            "interest_rate": "10.00",
            "number_of_installments": 12,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_generate_plan_twice(self):
        self.client.force_authenticate(user=self.superadmin)
        self.client.post(self.generate_url, {
            "interest_rate": "10.00", "number_of_installments": 12,
        }, format='json')

        response = self.client.post(self.generate_url, {
            "interest_rate": "5.00", "number_of_installments": 6,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_plan_for_nonexistent_project_returns_404(self):
        self.client.force_authenticate(user=self.superadmin)
        url = reverse('repayments:generate_plan', kwargs={'project_id': 999999})
        response = self.client.post(url, {
            "interest_rate": "10.00", "number_of_installments": 12,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PayInstallmentViewTests(APITestCase):
    """
    Tests de l'endpoint /repayments/<id>/pay/.
    """

    def setUp(self):
        self.superadmin = User.objects.create_user(
            email="piv_superadmin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )
        self.company_user = User.objects.create_user(
            email="piv_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="PIV SAS", registration_number="FR200200300"
        )
        self.company_wallet = Wallet.objects.get(user=self.company_user)
        TransactionService.deposit(self.company_wallet, Decimal('10000.00'))
        self.company_wallet.refresh_from_db()

        self.category = Category.objects.create(name="PIV Category")
        self.project = Project.objects.create(
            company=self.company, category=self.category, title="PIV Project",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('500.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )

        self.investor = User.objects.create_user(
            email="piv_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        InvestorProfile.objects.create(user=self.investor)
        self.wallet = Wallet.objects.get(user=self.investor)
        TransactionService.deposit(self.wallet, Decimal('500.00'))
        self.wallet.refresh_from_db()
        TransactionService.invest(self.wallet, self.project, Decimal('500.00'))
        self.project.refresh_from_db()

        self.plan = RepaymentService.generate_plan(
            self.project, interest_rate=Decimal('10.00'), number_of_installments=6
        )
        self.repayment = Repayment.objects.first()

        self.pay_url = reverse('repayments:pay_installment', kwargs={'pk': self.repayment.pk})

    def test_admin_can_pay_installment(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.post(self.pay_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Repayment.Status.PAID)

    def test_non_admin_cannot_pay_installment(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.post(self.pay_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_pay_nonexistent_installment(self):
        self.client.force_authenticate(user=self.superadmin)
        url = reverse('repayments:pay_installment', kwargs={'pk': 999999})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_pay_same_installment_twice_via_api(self):
        self.client.force_authenticate(user=self.superadmin)
        self.client.post(self.pay_url)

        response = self.client.post(self.pay_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MyRepaymentListViewTests(APITestCase):
    """
    Tests de l'endpoint /repayments/me/.
    """

    def setUp(self):
        self.investor = User.objects.create_user(
            email="mrl_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        InvestorProfile.objects.create(user=self.investor)
        self.wallet = Wallet.objects.get(user=self.investor)
        TransactionService.deposit(self.wallet, Decimal('300.00'))
        self.wallet.refresh_from_db()

        self.other_investor = User.objects.create_user(
            email="mrl_other_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        InvestorProfile.objects.create(user=self.other_investor)
        self.other_wallet = Wallet.objects.get(user=self.other_investor)
        TransactionService.deposit(self.other_wallet, Decimal('300.00'))
        self.other_wallet.refresh_from_db()

        self.company_user = User.objects.create_user(
            email="mrl_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="MRL SAS", registration_number="FR300300400"
        )
        self.category = Category.objects.create(name="MRL Category")
        self.project = Project.objects.create(
            company=self.company, category=self.category, title="MRL Project",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('600.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )
        TransactionService.invest(self.wallet, self.project, Decimal('300.00'))
        TransactionService.invest(self.other_wallet, self.project, Decimal('300.00'))
        self.project.refresh_from_db()

        RepaymentService.generate_plan(
            self.project, interest_rate=Decimal('10.00'), number_of_installments=3
        )

        self.me_url = reverse('repayments:my_repayments')

    def test_investor_sees_only_own_repayments(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # 3 echeances, toutes pour LUI
        for repayment in response.data:
            self.assertEqual(repayment['investor_email'], "mrl_investor@example.com")

    def test_unauthenticated_cannot_access(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProjectRepaymentPlanViewTests(APITestCase):
    """
    Tests de l'endpoint /repayments/plans/project/<project_id>/.
    """

    def setUp(self):
        self.owner_company_user = User.objects.create_user(
            email="prp_owner@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.owner_company = CompanyProfile.objects.create(
            user=self.owner_company_user, company_name="PRP Owner SAS", registration_number="FR400500600"
        )

        self.other_company_user = User.objects.create_user(
            email="prp_other_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        CompanyProfile.objects.create(
            user=self.other_company_user, company_name="PRP Other SAS", registration_number="FR700800900"
        )

        self.investor = User.objects.create_user(
            email="prp_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        InvestorProfile.objects.create(user=self.investor)
        wallet = Wallet.objects.get(user=self.investor)
        TransactionService.deposit(wallet, Decimal('200.00'))
        wallet.refresh_from_db()

        self.non_investor = User.objects.create_user(
            email="prp_non_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        InvestorProfile.objects.create(user=self.non_investor)

        self.superadmin = User.objects.create_user(
            email="prp_superadmin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )

        self.category = Category.objects.create(name="PRP Category")
        self.project = Project.objects.create(
            company=self.owner_company, category=self.category, title="PRP Project",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('200.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )
        TransactionService.invest(wallet, self.project, Decimal('200.00'))
        self.project.refresh_from_db()

        RepaymentService.generate_plan(
            self.project, interest_rate=Decimal('10.00'), number_of_installments=3
        )

        self.plan_url = reverse('repayments:project_plan', kwargs={'project_id': self.project.id})

    def test_owner_company_can_view_plan(self):
        self.client.force_authenticate(user=self.owner_company_user)
        response = self.client.get(self.plan_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_investor_who_invested_can_view_plan(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.plan_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_view_plan(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get(self.plan_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_company_cannot_view_plan(self):
        self.client.force_authenticate(user=self.other_company_user)
        response = self.client.get(self.plan_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_investor_cannot_view_plan(self):
        """Un investisseur qui N'A PAS investi dans ce projet ne doit pas voir le plan."""
        self.client.force_authenticate(user=self.non_investor)
        response = self.client.get(self.plan_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
