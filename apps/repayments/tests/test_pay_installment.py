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
from apps.transactions.models import Transaction
from apps.investments.models import Investment
from apps.repayments.models import Repayment
from apps.repayments.services import RepaymentService

User = get_user_model()


class PayInstallmentTests(TestCase):
    def setUp(self):
        self.company_user = User.objects.create_user(
            email="pi_company@example.com", password="Pass123!", role=User.Role.ENTREPRISE
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="PI SAS", registration_number="FR900800700"
        )
        self.company_wallet = Wallet.objects.get(user=self.company_user)
        TransactionService.deposit(self.company_wallet, Decimal('100000.00'))
        # IMPORTANT : rafraichir l'objet en memoire apres le depot -- deposit()
        # modifie le wallet via SON PROPRE exemplaire verrouille (select_for_update),
        # notre self.company_wallet local reste sinon perime (balance=0.00).
        self.company_wallet.refresh_from_db()

        self.category = Category.objects.create(name="PI Category")
        self.project = Project.objects.create(
            company=self.company, category=self.category, title="PI Project",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('1000.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )

        self.investor_user = User.objects.create_user(
            email="pi_investor@example.com", password="Pass123!", role=User.Role.INVESTISSEUR
        )
        self.investor_profile = InvestorProfile.objects.create(user=self.investor_user)
        self.investor_wallet = Wallet.objects.get(user=self.investor_user)
        TransactionService.deposit(self.investor_wallet, Decimal('1000.00'))
        self.investor_wallet.refresh_from_db()

        self.investment = TransactionService.invest(
            self.investor_wallet, self.project, Decimal('1000.00')
        ).investment
        self.investor_wallet.refresh_from_db()

        self.project.refresh_from_db()

        self.plan = RepaymentService.generate_plan(
            self.project, interest_rate=Decimal('12.00'), number_of_installments=12
        )
        self.first_repayment = Repayment.objects.get(investment=self.investment, installment_number=1)

    def test_pay_installment_marks_repayment_as_paid(self):
        RepaymentService.pay_installment(self.first_repayment)
        self.first_repayment.refresh_from_db()

        self.assertEqual(self.first_repayment.status, Repayment.Status.PAID)
        self.assertIsNotNone(self.first_repayment.paid_at)

    def test_pay_installment_credits_investor_wallet(self):
        total_due = self.first_repayment.total_amount
        initial_balance = self.investor_wallet.balance

        RepaymentService.pay_installment(self.first_repayment)

        self.investor_wallet.refresh_from_db()
        self.assertEqual(self.investor_wallet.balance, initial_balance + total_due)

    def test_pay_installment_debits_company_wallet(self):
        total_due = self.first_repayment.total_amount
        initial_balance = self.company_wallet.balance

        RepaymentService.pay_installment(self.first_repayment)

        self.company_wallet.refresh_from_db()
        self.assertEqual(self.company_wallet.balance, initial_balance - total_due)

    def test_pay_installment_creates_refund_and_interest_transactions(self):
        RepaymentService.pay_installment(self.first_repayment)

        refund_txn = Transaction.objects.filter(
            wallet=self.investor_wallet, transaction_type=Transaction.TransactionType.REFUND
        ).first()
        interest_txn = Transaction.objects.filter(
            wallet=self.investor_wallet, transaction_type=Transaction.TransactionType.INTEREST
        ).first()

        self.assertIsNotNone(refund_txn)
        self.assertIsNotNone(interest_txn)
        self.assertEqual(refund_txn.amount, self.first_repayment.capital_amount)
        self.assertEqual(interest_txn.amount, self.first_repayment.interest_amount)
        self.assertEqual(refund_txn.status, Transaction.Status.COMPLETED)
        self.assertEqual(interest_txn.status, Transaction.Status.COMPLETED)

    def test_pay_installment_updates_investment_amount_refunded(self):
        RepaymentService.pay_installment(self.first_repayment)

        self.investment.refresh_from_db()
        self.assertEqual(self.investment.amount_refunded, self.first_repayment.capital_amount)

    def test_investment_status_partially_refunded_after_one_installment(self):
        RepaymentService.pay_installment(self.first_repayment)

        self.investment.refresh_from_db()
        self.assertEqual(self.investment.status, Investment.Status.PARTIALLY_REFUNDED)

    def test_investment_status_fully_refunded_after_all_installments(self):
        all_repayments = Repayment.objects.filter(investment=self.investment).order_by('installment_number')

        for repayment in all_repayments:
            RepaymentService.pay_installment(repayment)

        self.investment.refresh_from_db()
        self.assertEqual(self.investment.status, Investment.Status.REFUNDED)
        self.assertEqual(self.investment.amount_refunded, self.investment.amount)

    def test_cannot_pay_already_paid_installment(self):
        RepaymentService.pay_installment(self.first_repayment)

        with self.assertRaises(ValidationError):
            RepaymentService.pay_installment(self.first_repayment)

    def test_insufficient_company_balance_raises_error(self):
        """Si l'entreprise n'a pas assez de fonds, le paiement doit echouer proprement."""
        # Vide le wallet entreprise -- self.company_wallet est a jour grace au
        # refresh_from_db() ajoute dans setUp().
        self.company_wallet.debit(self.company_wallet.available_balance)

        with self.assertRaises(ValidationError):
            RepaymentService.pay_installment(self.first_repayment)

        self.first_repayment.refresh_from_db()
        self.assertEqual(self.first_repayment.status, Repayment.Status.SCHEDULED)

    def test_failed_payment_leaves_no_partial_state(self):
        self.company_wallet.debit(self.company_wallet.available_balance)

        initial_investor_balance = self.investor_wallet.balance
        initial_amount_refunded = self.investment.amount_refunded
        initial_transaction_count = Transaction.objects.count()

        with self.assertRaises(ValidationError):
            RepaymentService.pay_installment(self.first_repayment)

        self.investor_wallet.refresh_from_db()
        self.investment.refresh_from_db()
        self.first_repayment.refresh_from_db()

        self.assertEqual(self.investor_wallet.balance, initial_investor_balance)
        self.assertEqual(self.investment.amount_refunded, initial_amount_refunded)
        self.assertEqual(self.first_repayment.status, Repayment.Status.SCHEDULED)
        self.assertEqual(Transaction.objects.count(), initial_transaction_count)

    def test_no_zero_amount_transaction_created_when_interest_rate_is_zero(self):
        zero_interest_project = Project.objects.create(
            company=self.company, category=self.category, title="Zero Interest Project",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('500.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )
        investor2_user = User.objects.create_user(
            email="pi_investor2@example.com", password="Pass123!", role=User.Role.INVESTISSEUR
        )
        InvestorProfile.objects.create(user=investor2_user)
        wallet2 = Wallet.objects.get(user=investor2_user)
        TransactionService.deposit(wallet2, Decimal('500.00'))
        wallet2.refresh_from_db()
        investment2 = TransactionService.invest(wallet2, zero_interest_project, Decimal('500.00')).investment
        zero_interest_project.refresh_from_db()

        plan = RepaymentService.generate_plan(
            zero_interest_project, interest_rate=Decimal('0.00'), number_of_installments=1
        )
        repayment = Repayment.objects.get(investment=investment2, installment_number=1)
        self.assertEqual(repayment.interest_amount, Decimal('0.00'))

        RepaymentService.pay_installment(repayment)

        interest_txn_exists = Transaction.objects.filter(
            wallet=wallet2, transaction_type=Transaction.TransactionType.INTEREST
        ).exists()
        self.assertFalse(interest_txn_exists)
class PlatformCommissionTests(TestCase):
    """
    Tests dedies au prelevement de la commission plateforme sur les interets.
    """

    def setUp(self):
        # Cree le compte PLATFORM explicitement (normalement fait une fois
        # en production via create_platform_account, absent par defaut en test).
        self.platform_user = User.objects.create(
            email="platform@crowdfunding.internal",
            first_name="Plateforme", last_name="Crowdfunding",
            role=User.Role.PLATFORM, is_email_verified=True,
        )
        self.platform_user.set_unusable_password()
        self.platform_user.save()
        self.platform_wallet = Wallet.objects.get(user=self.platform_user)

        self.company_user = User.objects.create_user(
            email="pc_company@example.com", password="Pass123!", role=User.Role.ENTREPRISE
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="PC SAS", registration_number="FR500600700"
        )
        self.company_wallet = Wallet.objects.get(user=self.company_user)
        TransactionService.deposit(self.company_wallet, Decimal('100000.00'))
        self.company_wallet.refresh_from_db()

        self.category = Category.objects.create(name="PC Category")
        self.project = Project.objects.create(
            company=self.company, category=self.category, title="PC Project",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('1000.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )

        self.investor_user = User.objects.create_user(
            email="pc_investor@example.com", password="Pass123!", role=User.Role.INVESTISSEUR
        )
        InvestorProfile.objects.create(user=self.investor_user)
        self.investor_wallet = Wallet.objects.get(user=self.investor_user)
        TransactionService.deposit(self.investor_wallet, Decimal('1000.00'))
        self.investor_wallet.refresh_from_db()

        self.investment = TransactionService.invest(
            self.investor_wallet, self.project, Decimal('1000.00')
        ).investment
        self.investor_wallet.refresh_from_db()
        self.project.refresh_from_db()

        self.plan = RepaymentService.generate_plan(
            self.project, interest_rate=Decimal('12.00'), number_of_installments=12
        )
        self.first_repayment = Repayment.objects.get(investment=self.investment, installment_number=1)

    def test_platform_wallet_credited_with_commission(self):
        """La plateforme doit recevoir sa commission (10% par defaut sur les interets)."""
        gross_interest = self.first_repayment.interest_amount

        RepaymentService.pay_installment(self.first_repayment)

        self.platform_wallet.refresh_from_db()
        expected_commission = (gross_interest * Decimal('0.10')).quantize(Decimal('0.01'))
        self.assertEqual(self.platform_wallet.balance, expected_commission)

    def test_investor_receives_net_interest_after_commission(self):
        """L'investisseur doit recevoir capital + interets NETS de commission."""
        gross_interest = self.first_repayment.interest_amount
        capital = self.first_repayment.capital_amount
        expected_commission = (gross_interest * Decimal('0.10')).quantize(Decimal('0.01'))
        expected_net_total = capital + (gross_interest - expected_commission)

        initial_balance = self.investor_wallet.balance
        RepaymentService.pay_installment(self.first_repayment)

        self.investor_wallet.refresh_from_db()
        self.assertEqual(self.investor_wallet.balance, initial_balance + expected_net_total)

    def test_capital_is_never_reduced_by_commission(self):
        """Le CAPITAL rembourse doit toujours etre integral -- seuls les interets sont taxes."""
        capital_before = self.first_repayment.capital_amount

        RepaymentService.pay_installment(self.first_repayment)

        refund_txn = Transaction.objects.filter(
            wallet=self.investor_wallet, transaction_type=Transaction.TransactionType.REFUND
        ).first()
        self.assertEqual(refund_txn.amount, capital_before)

    def test_commission_transaction_created_with_correct_type(self):
        RepaymentService.pay_installment(self.first_repayment)

        commission_txn = Transaction.objects.filter(
            wallet=self.platform_wallet, transaction_type=Transaction.TransactionType.COMMISSION
        ).first()
        self.assertIsNotNone(commission_txn)
        self.assertEqual(commission_txn.status, Transaction.Status.COMPLETED)

    def test_payment_succeeds_even_without_platform_account(self):
        """
        Si le compte PLATFORM n'existe pas (cas des autres tests de cette suite),
        le paiement doit tout de meme reussir -- l'investisseur recoit alors
        les interets BRUTS (pas de commission prelevee).
        """
        self.platform_user.delete()

        RepaymentService.pay_installment(self.first_repayment)

        self.first_repayment.refresh_from_db()
        self.assertEqual(self.first_repayment.status, Repayment.Status.PAID)