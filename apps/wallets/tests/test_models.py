from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.wallets.models import Wallet, WalletHistory

User = get_user_model()


class WalletModelTests(TestCase):
    """
    Tests unitaires du modele Wallet : credit, debit, lock, unlock,
    contraintes SQL, et coherence du solde disponible.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="wallet_model_test@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR
        )
        # Le signal a deja cree un wallet automatiquement -- on le recupere
        self.wallet = Wallet.objects.get(user=self.user)

    def test_wallet_auto_created_by_signal(self):
        """Un wallet doit exister automatiquement des la creation d'un investisseur."""
        self.assertIsNotNone(self.wallet)
        self.assertEqual(self.wallet.balance, Decimal('0.00'))

    def test_no_wallet_created_for_admin_roles(self):
        """Aucun wallet ne doit etre cree pour un SUPERADMIN/USERADMIN."""
        admin = User.objects.create_user(
            email="wallet_admin_test@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN
        )
        self.assertFalse(Wallet.objects.filter(user=admin).exists())

    def test_credit_increases_balance(self):
        self.wallet.credit(Decimal('100.00'), description="Depot initial")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('100.00'))

    def test_credit_creates_history_entry(self):
        self.wallet.credit(Decimal('50.00'), description="Test credit")
        history = self.wallet.history.first()
        self.assertEqual(history.movement_type, WalletHistory.MovementType.CREDIT)
        self.assertEqual(history.amount, Decimal('50.00'))
        self.assertEqual(history.balance_after, Decimal('50.00'))

    def test_credit_with_negative_amount_raises_error(self):
        with self.assertRaises(ValidationError):
            self.wallet.credit(Decimal('-10.00'))

    def test_debit_decreases_balance(self):
        self.wallet.credit(Decimal('100.00'))
        self.wallet.debit(Decimal('30.00'), description="Retrait test")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('70.00'))

    def test_debit_more_than_available_raises_error(self):
        self.wallet.credit(Decimal('50.00'))
        with self.assertRaises(ValidationError):
            self.wallet.debit(Decimal('100.00'))

    def test_lock_funds_reduces_available_balance_only(self):
        """Bloquer des fonds ne doit PAS changer balance, seulement locked_balance."""
        self.wallet.credit(Decimal('200.00'))
        self.wallet.lock_funds(Decimal('80.00'), description="Investissement en cours")
        self.wallet.refresh_from_db()

        self.assertEqual(self.wallet.balance, Decimal('200.00'))
        self.assertEqual(self.wallet.locked_balance, Decimal('80.00'))
        self.assertEqual(self.wallet.available_balance, Decimal('120.00'))

    def test_lock_funds_more_than_available_raises_error(self):
        self.wallet.credit(Decimal('50.00'))
        with self.assertRaises(ValidationError):
            self.wallet.lock_funds(Decimal('100.00'))

    def test_unlock_funds_restores_available_balance(self):
        self.wallet.credit(Decimal('200.00'))
        self.wallet.lock_funds(Decimal('80.00'))
        self.wallet.unlock_funds(Decimal('30.00'), description="Investissement annule partiellement")
        self.wallet.refresh_from_db()

        self.assertEqual(self.wallet.locked_balance, Decimal('50.00'))
        self.assertEqual(self.wallet.available_balance, Decimal('150.00'))

    def test_unlock_more_than_locked_raises_error(self):
        self.wallet.credit(Decimal('100.00'))
        self.wallet.lock_funds(Decimal('40.00'))
        with self.assertRaises(ValidationError):
            self.wallet.unlock_funds(Decimal('50.00'))

    def test_debit_cannot_touch_locked_funds(self):
        """Un debit standard ne doit jamais pouvoir prelever sur les fonds bloques."""
        self.wallet.credit(Decimal('100.00'))
        self.wallet.lock_funds(Decimal('60.00'))
        # available_balance = 40.00 -- tenter de debiter 50.00 doit echouer
        with self.assertRaises(ValidationError):
            self.wallet.debit(Decimal('50.00'))

    def test_database_constraint_prevents_negative_balance(self):
        """
        Meme en contournant la logique Python (via update() direct),
        la contrainte SQL doit refuser un solde negatif.
        """
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Wallet.objects.filter(pk=self.wallet.pk).update(balance=Decimal('-10.00'))

    def test_database_constraint_prevents_locked_exceeding_balance(self):
        """La contrainte SQL doit refuser locked_balance > balance."""
        self.wallet.credit(Decimal('50.00'))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Wallet.objects.filter(pk=self.wallet.pk).update(locked_balance=Decimal('100.00'))

    def test_history_is_ordered_most_recent_first(self):
        self.wallet.credit(Decimal('10.00'))
        self.wallet.credit(Decimal('20.00'))
        history_entries = list(self.wallet.history.all())
        self.assertEqual(history_entries[0].amount, Decimal('20.00'))
        self.assertEqual(history_entries[1].amount, Decimal('10.00'))
