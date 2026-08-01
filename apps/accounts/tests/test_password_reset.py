from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()
password_reset_token = PasswordResetTokenGenerator()


class PasswordResetTests(APITestCase):
    """
    Tests du flux de réinitialisation de mot de passe.
    """

    def setUp(self):
        self.request_url = reverse('accounts:password_reset_request')
        self.confirm_url = reverse('accounts:password_reset_confirm')
        self.login_url = reverse('accounts:login')

        self.user = User.objects.create_user(
            email="resetflow@example.com",
            password="OldPass123!",
            is_email_verified=True
        )

        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = password_reset_token.make_token(self.user)

    def test_reset_request_with_existing_email_returns_200(self):
        """Une demande avec un email existant doit renvoyer 200."""
        response = self.client.post(self.request_url, {"email": "resetflow@example.com"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reset_request_with_nonexistent_email_returns_same_response(self):
        """
        Une demande avec un email INEXISTANT doit renvoyer EXACTEMENT
        la même réponse (200 + même message), pour ne jamais révéler
        si un email est enregistré dans le système.
        """
        response_existing = self.client.post(self.request_url, {"email": "resetflow@example.com"}, format='json')
        response_nonexistent = self.client.post(self.request_url, {"email": "doesnotexist@example.com"}, format='json')

        self.assertEqual(response_existing.status_code, response_nonexistent.status_code)
        self.assertEqual(response_existing.data['detail'], response_nonexistent.data['detail'])

    def test_reset_confirm_with_valid_token_succeeds(self):
        """Une confirmation avec uid/token valides doit changer le mot de passe."""
        response = self.client.post(self.confirm_url, {
            "uid": self.uid,
            "token": self.token,
            "new_password": "NewPass456!",
            "new_password2": "NewPass456!",
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Vérifie que le NOUVEAU mot de passe fonctionne réellement pour se connecter
        login_response = self.client.post(self.login_url, {
            "email": "resetflow@example.com",
            "password": "NewPass456!"
        }, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_reset_confirm_password_mismatch_fails(self):
        """Si new_password et new_password2 diffèrent, la confirmation doit échouer."""
        response = self.client.post(self.confirm_url, {
            "uid": self.uid,
            "token": self.token,
            "new_password": "NewPass456!",
            "new_password2": "DifferentPass789!",
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_confirm_invalid_token_fails(self):
        """Un token invalide doit être rejeté."""
        response = self.client.post(self.confirm_url, {
            "uid": self.uid,
            "token": "token-invalide-bidon",
            "new_password": "NewPass456!",
            "new_password2": "NewPass456!",
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_confirm_invalid_uid_fails(self):
        """Un uid invalide/non décodable doit être rejeté."""
        response = self.client.post(self.confirm_url, {
            "uid": "uid-invalide-xyz",
            "token": self.token,
            "new_password": "NewPass456!",
            "new_password2": "NewPass456!",
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_old_password_no_longer_works_after_reset(self):
        """Après réinitialisation, l'ANCIEN mot de passe ne doit plus fonctionner."""
        self.client.post(self.confirm_url, {
            "uid": self.uid,
            "token": self.token,
            "new_password": "NewPass456!",
            "new_password2": "NewPass456!",
        }, format='json')

        login_response = self.client.post(self.login_url, {
            "email": "resetflow@example.com",
            "password": "OldPass123!"
        }, format='json')

        self.assertEqual(login_response.status_code, status.HTTP_401_UNAUTHORIZED)
