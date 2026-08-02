from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.companies.models import CompanyProfile
from apps.investors.models import InvestorProfile
from apps.projects.models import Category, Project
from apps.transactions.models import Transaction
from apps.investments.models import Investment
from apps.wallets.models import Wallet

User = get_user_model()


class InvestmentModelTests(TestCase):
    """
    Tests unitaires du modele Investment.
    """

    def setUp(self):
        self.investor_user = User.objects.create_user(
            email="im_investor@example.com", password="Pass123!", role=User.Role.INVESTISSEUR
        )
        self.investor_profile = InvestorProfile.objects.create(user=self.investor_user)
        self.wallet = Wallet.objects.get(user=self.investor_user)

        self.company_user = User.objects.create_user(
            email="im_company@example.com", password="Pass123!", role=User.Role.ENTREPRISE
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="IM SAS", registration_number="FR000222333"
        )
        self.category = Category.objects.create(name="IM Category")
        self.project = Project.objects.create(
            company=self.company, category=self.category, title="Projet IM",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('1000.00'),
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )

        self.transaction = Transaction.objects.create(
            wallet=self.wallet, project=self.project,
            transaction_type=Transaction.TransactionType.INVESTMENT,
            amount=Decimal('100.00'), status=Transaction.Status.COMPLETED,
        )

    def test_investment_created_with_default_active_status(self):
        investment = Investment.objects.create(
            investor_profile=self.investor_profile, project=self.project,
            transaction=self.transaction, amount=Decimal('100.00'),
        )
        self.assertEqual(investment.status, Investment.Status.ACTIVE)

    def test_remaining_amount_equals_amount_when_no_refund(self):
        investment = Investment.objects.create(
            investor_profile=self.investor_profile, project=self.project,
            transaction=self.transaction, amount=Decimal('100.00'),
        )
        self.assertEqual(investment.remaining_amount, Decimal('100.00'))

    def test_remaining_amount_decreases_with_partial_refund(self):
        investment = Investment.objects.create(
            investor_profile=self.investor_profile, project=self.project,
            transaction=self.transaction, amount=Decimal('100.00'),
            amount_refunded=Decimal('40.00'),
        )
        self.assertEqual(investment.remaining_amount, Decimal('60.00'))

    def test_transaction_link_is_unique(self):
        """
        Une Transaction ne peut etre liee qu'a UN SEUL Investment
        (contrainte OneToOneField au niveau base de donnees).
        """
        Investment.objects.create(
            investor_profile=self.investor_profile, project=self.project,
            transaction=self.transaction, amount=Decimal('100.00'),
        )
        with self.assertRaises(Exception):
            Investment.objects.create(
                investor_profile=self.investor_profile, project=self.project,
                transaction=self.transaction, amount=Decimal('50.00'),
            )

    def test_multiple_investments_allowed_for_same_investor_and_project(self):
        """
        PAS de contrainte d'unicite (investor, project) -- un investisseur
        peut renforcer sa position avec plusieurs Investment distincts,
        chacun lie a sa PROPRE transaction.
        """
        txn2 = Transaction.objects.create(
            wallet=self.wallet, project=self.project,
            transaction_type=Transaction.TransactionType.INVESTMENT,
            amount=Decimal('50.00'), status=Transaction.Status.COMPLETED,
        )

        Investment.objects.create(
            investor_profile=self.investor_profile, project=self.project,
            transaction=self.transaction, amount=Decimal('100.00'),
        )
        Investment.objects.create(
            investor_profile=self.investor_profile, project=self.project,
            transaction=txn2, amount=Decimal('50.00'),
        )

        count = Investment.objects.filter(
            investor_profile=self.investor_profile, project=self.project
        ).count()
        self.assertEqual(count, 2)

    def test_string_representation(self):
        investment = Investment.objects.create(
            investor_profile=self.investor_profile, project=self.project,
            transaction=self.transaction, amount=Decimal('100.00'),
        )
        self.assertIn("im_investor@example.com", str(investment))
        self.assertIn("Projet IM", str(investment))
