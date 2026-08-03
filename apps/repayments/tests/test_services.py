from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.companies.models import CompanyProfile
from apps.investors.models import InvestorProfile
from apps.projects.models import Category, Project
from apps.wallets.models import Wallet
from apps.transactions.services import TransactionService
from apps.investments.models import Investment
from apps.repayments.models import RepaymentPlan, Repayment
from apps.repayments.services import RepaymentService

User = get_user_model()


class SplitAmountTests(TestCase):
    """
    Tests UNITAIRES de la methode critique _split_amount_among_investments().
    """

    _investor_counter = 0

    def setUp(self):
        self.company_user = User.objects.create_user(
            email="split_company@example.com", password="Pass123!", role=User.Role.ENTREPRISE
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="Split SAS", registration_number="FR100200300"
        )
        self.category = Category.objects.create(name="Split Category")
        self.project = Project.objects.create(
            company=self.company, category=self.category, title="Split Project",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('10000.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )

    def _make_fake_investment(self, amount):
        """
        Cree un Investment via le vrai flux (Wallet -> Transaction -> Investment).
        Utilise un COMPTEUR pour l'email (pas le montant), car plusieurs
        investisseurs peuvent avoir investi le MEME montant.
        """
        type(self)._investor_counter += 1
        investor_user = User.objects.create_user(
            email=f"split_investor_{type(self)._investor_counter}@example.com",
            password="Pass123!", role=User.Role.INVESTISSEUR
        )
        investor_profile = InvestorProfile.objects.create(user=investor_user)
        wallet = Wallet.objects.get(user=investor_user)
        TransactionService.deposit(wallet, amount)
        return TransactionService.invest(wallet, self.project, amount).investment

    def test_split_two_equal_investments(self):
        inv1 = self._make_fake_investment(Decimal('500.00'))
        inv2 = self._make_fake_investment(Decimal('500.00'))

        splits = RepaymentService._split_amount_among_investments(
            Decimal('500.00'), [inv1, inv2]
        )

        amounts = [part for _, part in splits]
        self.assertEqual(amounts, [Decimal('250.00'), Decimal('250.00')])
        self.assertEqual(sum(amounts), Decimal('500.00'))

    def test_split_sum_always_equals_total_even_with_rounding(self):
        inv1 = self._make_fake_investment(Decimal('333.33'))
        inv2 = self._make_fake_investment(Decimal('333.33'))
        inv3 = self._make_fake_investment(Decimal('333.34'))

        splits = RepaymentService._split_amount_among_investments(
            Decimal('100.00'), [inv1, inv2, inv3]
        )

        amounts = [part for _, part in splits]
        self.assertEqual(sum(amounts), Decimal('100.00'))

    def test_split_with_uneven_proportions(self):
        inv_jean = self._make_fake_investment(Decimal('250.00'))
        inv_marie = self._make_fake_investment(Decimal('750.00'))

        splits = RepaymentService._split_amount_among_investments(
            Decimal('1000.00'), [inv_jean, inv_marie]
        )

        splits_dict = {inv.id: part for inv, part in splits}
        self.assertEqual(splits_dict[inv_jean.id], Decimal('250.00'))
        self.assertEqual(splits_dict[inv_marie.id], Decimal('750.00'))

    def test_split_with_many_investments_sum_is_exact(self):
        amounts_invested = [Decimal('111.11'), Decimal('222.22'), Decimal('333.33'),
                             Decimal('44.44'), Decimal('555.55'), Decimal('66.66'), Decimal('777.77')]
        investments = [self._make_fake_investment(amt) for amt in amounts_invested]

        total_to_split = Decimal('1000.00')
        splits = RepaymentService._split_amount_among_investments(total_to_split, investments)

        amounts = [part for _, part in splits]
        self.assertEqual(sum(amounts), total_to_split)

    def test_split_single_investment_receives_full_amount(self):
        inv = self._make_fake_investment(Decimal('500.00'))
        splits = RepaymentService._split_amount_among_investments(Decimal('123.45'), [inv])
        self.assertEqual(splits[0][1], Decimal('123.45'))

    def test_split_empty_list_returns_empty(self):
        splits = RepaymentService._split_amount_among_investments(Decimal('100.00'), [])
        self.assertEqual(splits, [])


class GeneratePlanTests(TestCase):
    def setUp(self):
        self.company_user = User.objects.create_user(
            email="gp_company@example.com", password="Pass123!", role=User.Role.ENTREPRISE
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="GP SAS", registration_number="FR200300400"
        )
        self.category = Category.objects.create(name="GP Category")
        self.project = Project.objects.create(
            company=self.company, category=self.category, title="GP Project",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('1000.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )

        self.investor1_user = User.objects.create_user(
            email="gp_investor1@example.com", password="Pass123!", role=User.Role.INVESTISSEUR
        )
        InvestorProfile.objects.create(user=self.investor1_user)
        wallet1 = Wallet.objects.get(user=self.investor1_user)
        TransactionService.deposit(wallet1, Decimal('600.00'))
        TransactionService.invest(wallet1, self.project, Decimal('600.00'))

        self.investor2_user = User.objects.create_user(
            email="gp_investor2@example.com", password="Pass123!", role=User.Role.INVESTISSEUR
        )
        InvestorProfile.objects.create(user=self.investor2_user)
        wallet2 = Wallet.objects.get(user=self.investor2_user)
        TransactionService.deposit(wallet2, Decimal('400.00'))
        TransactionService.invest(wallet2, self.project, Decimal('400.00'))

        self.project.refresh_from_db()

    def test_generate_plan_creates_plan_with_correct_totals(self):
        plan = RepaymentService.generate_plan(
            self.project, interest_rate=Decimal('10.00'), number_of_installments=12
        )
        self.assertEqual(plan.total_capital, Decimal('1000.00'))
        self.assertEqual(plan.status, RepaymentPlan.Status.ACTIVE)

    def test_generate_plan_creates_correct_number_of_repayments(self):
        RepaymentService.generate_plan(
            self.project, interest_rate=Decimal('10.00'), number_of_installments=12
        )
        self.assertEqual(Repayment.objects.count(), 24)

    def test_sum_of_all_capital_repayments_equals_total_capital(self):
        plan = RepaymentService.generate_plan(
            self.project, interest_rate=Decimal('10.00'), number_of_installments=12
        )
        total_capital_distributed = sum(
            r.capital_amount for r in Repayment.objects.filter(plan=plan)
        )
        self.assertEqual(total_capital_distributed, plan.total_capital)

    def test_sum_of_all_interest_repayments_equals_total_interest(self):
        plan = RepaymentService.generate_plan(
            self.project, interest_rate=Decimal('10.00'), number_of_installments=12
        )
        total_interest_distributed = sum(
            r.interest_amount for r in Repayment.objects.filter(plan=plan)
        )
        self.assertEqual(total_interest_distributed, plan.total_interest)

    def test_each_investor_receives_proportional_share(self):
        plan = RepaymentService.generate_plan(
            self.project, interest_rate=Decimal('10.00'), number_of_installments=12
        )

        investment1 = Investment.objects.get(investor_profile__user=self.investor1_user)
        investment2 = Investment.objects.get(investor_profile__user=self.investor2_user)

        repayment1_installment1 = Repayment.objects.get(investment=investment1, installment_number=1)
        repayment2_installment1 = Repayment.objects.get(investment=investment2, installment_number=1)

        total_installment1 = repayment1_installment1.total_amount + repayment2_installment1.total_amount

        expected_ratio = Decimal('600.00') / Decimal('1000.00')
        actual_ratio = repayment1_installment1.total_amount / total_installment1
        self.assertAlmostEqual(float(actual_ratio), float(expected_ratio), places=2)

    def test_cannot_generate_plan_twice_for_same_project(self):
        RepaymentService.generate_plan(
            self.project, interest_rate=Decimal('10.00'), number_of_installments=12
        )
        with self.assertRaises(ValidationError):
            RepaymentService.generate_plan(
                self.project, interest_rate=Decimal('5.00'), number_of_installments=6
            )

    def test_cannot_generate_plan_without_active_investments(self):
        empty_project = Project.objects.create(
            company=self.company, category=self.category, title="Empty Project",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('1000.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )
        with self.assertRaises(ValidationError):
            RepaymentService.generate_plan(
                empty_project, interest_rate=Decimal('10.00'), number_of_installments=12
            )

    def test_installments_are_scheduled_with_increasing_due_dates(self):
        plan = RepaymentService.generate_plan(
            self.project, interest_rate=Decimal('10.00'), number_of_installments=3, frequency_days=30
        )
        investment1 = Investment.objects.get(investor_profile__user=self.investor1_user)
        repayments = Repayment.objects.filter(investment=investment1).order_by('installment_number')

        due_dates = [r.due_date for r in repayments]
        self.assertEqual(due_dates, sorted(due_dates))
        self.assertEqual((due_dates[1] - due_dates[0]).days, 30)
