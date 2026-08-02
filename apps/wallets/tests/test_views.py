from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.wallets.models import Wallet

User = get_user_model()


class MyWalletViewTests(APITestCase):
    """
    Tests de l'endpoint /wallet/me/ : consultation du propre portefeuille.
    """

    def setUp(self):
        self.me_url = reverse('wallets:my_wallet')

        self.investor = User.objects.create_user(
            email="mw_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.admin = User.objects.create_user(
            email="mw_admin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )

    def test_investor_can_see_own_wallet(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['balance'], '0.00')

    def test_admin_without_wallet_gets_404(self):
        """Un admin sans wallet doit recevoir un 404 explicite, pas une erreur 500."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_access_wallet(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wallet_endpoint_does_not_expose_write_methods(self):
        """PATCH doit etre refuse (405), meme pour le proprietaire du wallet."""
        self.client.force_authenticate(user=self.investor)
        response = self.client.patch(self.me_url, {"balance": "999999.00"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class WalletListViewTests(APITestCase):
    """
    Tests de l'endpoint /wallets/ : audit reserve a l'administration.
    """

    def setUp(self):
        self.list_url = reverse('wallets:wallet_list')

        self.superadmin = User.objects.create_user(
            email="wl_superadmin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )
        self.investor = User.objects.create_user(
            email="wl_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )

    def test_admin_can_list_all_wallets(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Le wallet de self.investor uniquement

    def test_investor_cannot_list_all_wallets(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_endpoint_does_not_expose_write_methods(self):
        self.client.force_authenticate(user=self.superadmin)
        wallet = Wallet.objects.get(user=self.investor)
        detail_url = reverse('wallets:wallet_detail', kwargs={'pk': wallet.pk})

        response = self.client.patch(detail_url, {"balance": "999999.00"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class WalletDetailViewTests(APITestCase):
    """
    Tests de l'endpoint /wallets/<id>/ : consultation d'un wallet precis par l'admin.
    """

    def setUp(self):
        self.superadmin = User.objects.create_user(
            email="wd_superadmin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )
        self.investor = User.objects.create_user(
            email="wd_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.other_investor = User.objects.create_user(
            email="wd_other@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )

        self.wallet = Wallet.objects.get(user=self.investor)
        self.detail_url = reverse('wallets:wallet_detail', kwargs={'pk': self.wallet.pk})

    def test_admin_can_view_any_wallet_detail(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_investor_cannot_view_wallet_detail_endpoint(self):
        """L'endpoint /wallets/<id>/ est reserve a l'admin, meme pour son PROPRE wallet
        (l'investisseur doit utiliser /wallet/me/ a la place)."""
        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_investor_cannot_view_wallet_detail(self):
        self.client.force_authenticate(user=self.other_investor)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
