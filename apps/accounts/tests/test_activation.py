from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.tokens import account_activation_token

User = get_user_model()


class ActivationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="activation@example.com",
            password="TestPass123!"
        )
        self.assertFalse(self.user.is_email_verified)

        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = account_activation_token.make_token(self.user)

        self.login_url = reverse('accounts:login')

    def _activation_url(self, uid, token):
        return reverse('accounts:activate', kwargs={'uidb64': uid, 'token': token})

    def test_activation_with_valid_token_succeeds(self):
        url = self._activation_url(self.uid, self.token)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

    def test_activation_link_reuse_returns_already_active_message(self):
        url = self._activation_url(self.uid, self.token)
        self.client.get(url)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("déjà activé", response.data['detail'])

    def test_activation_with_invalid_token_fails(self):
        url = self._activation_url(self.uid, "token-completement-invalide")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)

    def test_activation_with_invalid_uid_fails(self):
        url = self._activation_url("uid-invalide-xyz", self.token)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_blocked_before_activation(self):
        response = self.client.post(self.login_url, {
            "email": "activation@example.com",
            "password": "TestPass123!"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_allowed_after_activation(self):
        url = self._activation_url(self.uid, self.token)
        self.client.get(url)
        response = self.client.post(self.login_url, {
            "email": "activation@example.com",
            "password": "TestPass123!"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
