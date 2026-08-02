from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.companies.models import CompanyProfile
from apps.projects.models import Category, Project
from apps.wallets.models import Wallet
from apps.transactions.models import Transaction
from apps.transactions.services import TransactionService, InsufficientFundsError

User = get_user_model()


class DepositServiceTests(TestCase):
    """
    Tests du service TransactionService.deposit().
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="deposit_test@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR
        )
        self.wallet = Wallet.objects.get(user=self.user)

    def test_deposit_creates_completed_transaction(self):
        txn = TransactionService.deposit(self.wallet, Decimal('100.00'), description="Test depot")

        self.assertEqual(txn.status, Transaction.Status.COMPLETED)
        self.assertEqual(txn.transaction_type, Transaction.TransactionType.DEPOSIT)
        self.assertEqual(txn.amount, Decimal('100.00'))

    def test_deposit_increases_wallet_balance(self):
        TransactionService.deposit(self.wallet, Decimal('150.00'))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('150.00'))

    def test_deposit_has_unique_reference(self):
        txn1 = TransactionService.deposit(self.wallet, Decimal('10.00'))
        txn2 = TransactionService.deposit(self.wallet, Decimal('20.00'))
        self.assertNotEqual(txn1.reference, txn2.reference)


class WithdrawServiceTests(TestCase):
    """
    Tests du service TransactionService.withdraw().
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="withdraw_test@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR
        )
        self.wallet = Wallet.objects.get(user=self.user)
        TransactionService.deposit(self.wallet, Decimal('200.00'))
        self.wallet.refresh_from_db()

    def test_withdraw_creates_completed_transaction(self):
        txn = TransactionService.withdraw(self.wallet, Decimal('50.00'))
        self.assertEqual(txn.status, Transaction.Status.COMPLETED)
        self.assertEqual(txn.transaction_type, Transaction.TransactionType.WITHDRAWAL)

    def test_withdraw_decreases_wallet_balance(self):
        TransactionService.withdraw(self.wallet, Decimal('80.00'))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('120.00'))

    def test_withdraw_more_than_available_raises_error_and_creates_no_transaction(self):
        """
        Point CRITIQUE : si le retrait echoue, AUCUNE transaction ne doit
        rester en base (grace a l'atomicite) -- pas de trace fantome PENDING.
        """
        initial_count = Transaction.objects.count()

        with self.assertRaises(InsufficientFundsError):
            TransactionService.withdraw(self.wallet, Decimal('500.00'))

        self.assertEqual(Transaction.objects.count(), initial_count)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('200.00'))  # Inchange


class InvestServiceTests(TestCase):
    """
    Tests du service TransactionService.invest() -- l'operation la plus critique.
    """

    def setUp(self):
        # Investisseur avec des fonds
        self.investor_user = User.objects.create_user(
            email="invest_test@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR
        )
        self.investor_wallet = Wallet.objects.get(user=self.investor_user)
        TransactionService.deposit(self.investor_wallet, Decimal('1000.00'))
        self.investor_wallet.refresh_from_db()

        # Entreprise + projet ACTIVE
        self.company_user = User.objects.create_user(
            email="invest_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="Invest SAS", registration_number="FR111000111"
        )
        self.category = Category.objects.create(name="Test Category Invest")

        self.active_project = Project.objects.create(
            company=self.company, category=self.category, title="Projet Actif",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('500.00'),
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )

        self.draft_project = Project.objects.create(
            company=self.company, category=self.category, title="Projet Brouillon",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('500.00'),
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status=Project.Status.DRAFT,
        )

    def test_invest_creates_completed_transaction_linked_to_project(self):
        txn = TransactionService.invest(self.investor_wallet, self.active_project, Decimal('100.00'))

        self.assertEqual(txn.status, Transaction.Status.COMPLETED)
        self.assertEqual(txn.transaction_type, Transaction.TransactionType.INVESTMENT)
        self.assertEqual(txn.project, self.active_project)

    def test_invest_debits_investor_wallet(self):
        TransactionService.invest(self.investor_wallet, self.active_project, Decimal('300.00'))
        self.investor_wallet.refresh_from_db()
        self.assertEqual(self.investor_wallet.balance, Decimal('700.00'))

    def test_invest_credits_project_current_amount(self):
        TransactionService.invest(self.investor_wallet, self.active_project, Decimal('150.00'))
        self.active_project.refresh_from_db()
        self.assertEqual(self.active_project.current_amount, Decimal('150.00'))

    def test_invest_in_non_active_project_raises_error(self):
        """On ne peut PAS investir dans un projet DRAFT (is_open_for_investment=False)."""
        with self.assertRaises(ValidationError):
            TransactionService.invest(self.investor_wallet, self.draft_project, Decimal('50.00'))

        # Aucune transaction ne doit avoir ete creee
        self.assertFalse(
            Transaction.objects.filter(project=self.draft_project).exists()
        )

    def test_invest_more_than_available_balance_raises_error(self):
        with self.assertRaises(InsufficientFundsError):
            TransactionService.invest(self.investor_wallet, self.active_project, Decimal('5000.00'))

        self.investor_wallet.refresh_from_db()
        self.assertEqual(self.investor_wallet.balance, Decimal('1000.00'))  # Inchange

    def test_invest_exceeding_funding_goal_raises_error(self):
        """L'investissement ne doit jamais faire depasser current_amount au-dela de funding_goal."""
        # funding_goal = 500.00 -- tenter d'investir 600.00 doit echouer
        with self.assertRaises(ValidationError):
            TransactionService.invest(self.investor_wallet, self.active_project, Decimal('600.00'))

        self.active_project.refresh_from_db()
        self.assertEqual(self.active_project.current_amount, Decimal('0.00'))  # Inchange

    def test_multiple_investments_accumulate_correctly(self):
        """Plusieurs investissements successifs doivent s'accumuler correctement sur le projet."""
        TransactionService.invest(self.investor_wallet, self.active_project, Decimal('100.00'))
        TransactionService.invest(self.investor_wallet, self.active_project, Decimal('200.00'))

        self.active_project.refresh_from_db()
        self.assertEqual(self.active_project.current_amount, Decimal('300.00'))

        self.investor_wallet.refresh_from_db()
        self.assertEqual(self.investor_wallet.balance, Decimal('700.00'))

    def test_failed_investment_leaves_no_partial_state(self):
        """
        Test le plus important de cette etape : verifie qu'un echec
        (ici, depassement d'objectif) ne laisse AUCUNE trace partielle --
        ni transaction, ni modification du wallet, ni modification du projet.
        C'est la preuve concrete que l'atomicite fonctionne.
        """
        initial_wallet_balance = self.investor_wallet.balance
        initial_project_amount = self.active_project.current_amount
        initial_transaction_count = Transaction.objects.count()

        with self.assertRaises(ValidationError):
            TransactionService.invest(self.investor_wallet, self.active_project, Decimal('600.00'))

        self.investor_wallet.refresh_from_db()
        self.active_project.refresh_from_db()

        self.assertEqual(self.investor_wallet.balance, initial_wallet_balance)
        self.assertEqual(self.active_project.current_amount, initial_project_amount)
        self.assertEqual(Transaction.objects.count(), initial_transaction_count)
