from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RegisterTests(APITestCase):
    """
    Tests de l'endpoint d'inscription (/api/v1/accounts/register/).
    """

    def setUp(self):
        # reverse() construit l'URL à partir du name défini dans accounts/urls.py
        # 'accounts:register' = app_name 'accounts' + name 'register'
        self.register_url = reverse('accounts:register')
        self.valid_payload = {
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "password2": "StrongPass123!",
            "first_name": "Alice",
            "last_name": "Durand",
            "role": "INVESTISSEUR",
        }

    def test_register_success(self):
        """L'inscription avec des données valides doit créer un utilisateur et retourner des tokens."""
        response = self.client.post(self.register_url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])

        # Vérifie que l'utilisateur existe bien réellement en base
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_register_password_mismatch(self):
        """Si password et password2 diffèrent, l'inscription doit échouer avec une erreur 400."""
        payload = self.valid_payload.copy()
        payload['password2'] = "DifferentPass123!"

        response = self.client.post(self.register_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_register_duplicate_email(self):
        """Deux comptes ne peuvent pas partager le même email."""
        # Premier enregistrement : doit réussir
        self.client.post(self.register_url, self.valid_payload, format='json')

        # Deuxième tentative avec le même email : doit échouer
        response = self.client.post(self.register_url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_register_weak_password_rejected(self):
        """Un mot de passe trop simple doit être rejeté par les validateurs Django."""
        payload = self.valid_payload.copy()
        payload['password'] = "12345678"
        payload['password2'] = "12345678"

        response = self.client.post(self.register_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    """
    Tests de l'endpoint de connexion (/api/v1/accounts/login/).
    """

    def setUp(self):
        self.login_url = reverse('accounts:login')

        # On crée directement l'utilisateur en base (sans passer par /register/)
        # car ce test se concentre uniquement sur le comportement du LOGIN
        self.user = User.objects.create_user(
            email="logintest@example.com",
            password="StrongPass123!"
        )

    def test_login_success(self):
        """Une connexion avec des identifiants valides doit retourner access + refresh."""
        response = self.client.post(self.login_url, {
            "email": "logintest@example.com",
            "password": "StrongPass123!"
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_wrong_password(self):
        """Un mauvais mot de passe doit être rejeté avec un 401."""
        response = self.client.post(self.login_url, {
            "email": "logintest@example.com",
            "password": "WrongPassword!"
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_email(self):
        """Un email inexistant doit être rejeté avec un 401 (pas d'indice sur l'existence du compte)."""
        response = self.client.post(self.login_url, {
            "email": "doesnotexist@example.com",
            "password": "StrongPass123!"
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MeEndpointTests(APITestCase):
    """
    Tests de l'endpoint /me/, qui nécessite une authentification.
    """

    def setUp(self):
        self.me_url = reverse('accounts:me')
        self.user = User.objects.create_user(
            email="metest@example.com",
            password="StrongPass123!"
        )

    def test_me_requires_authentication(self):
        """Sans token, l'accès à /me/ doit être refusé (401)."""
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_with_valid_token(self):
        """Avec un token valide, /me/ doit renvoyer les infos du bon utilisateur."""
        # force_authenticate simule une authentification sans passer par un vrai token JWT
        # -> utile pour tester la logique de la vue elle-même, indépendamment du système JWT
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], "metest@example.com")


class RefreshAndLogoutTests(APITestCase):
    """
    Tests de rotation des refresh tokens et de la blacklist (Refresh + Logout).
    """

    def setUp(self):
        self.login_url = reverse('accounts:login')
        self.refresh_url = reverse('accounts:login_refresh')
        self.logout_url = reverse('accounts:logout')

        self.user = User.objects.create_user(
            email="tokentest@example.com",
            password="StrongPass123!"
        )

        # On se connecte réellement pour obtenir un vrai couple access/refresh
        login_response = self.client.post(self.login_url, {
            "email": "tokentest@example.com",
            "password": "StrongPass123!"
        }, format='json')

        self.access_token = login_response.data['access']
        self.refresh_token = login_response.data['refresh']

    def test_refresh_rotates_token(self):
        """Un refresh valide doit renvoyer un NOUVEAU couple access + refresh (rotation activée)."""
        response = self.client.post(self.refresh_url, {
            "refresh": self.refresh_token
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        # Le nouveau refresh doit être différent de l'ancien (preuve de rotation)
        self.assertNotEqual(response.data['refresh'], self.refresh_token)

    def test_old_refresh_token_is_blacklisted_after_rotation(self):
        """Après une rotation, l'ANCIEN refresh token ne doit plus être utilisable."""
        # Première utilisation : doit réussir et blacklister l'ancien token
        self.client.post(self.refresh_url, {"refresh": self.refresh_token}, format='json')

        # Deuxième utilisation du MÊME (ancien) refresh token : doit échouer
        response = self.client.post(self.refresh_url, {"refresh": self.refresh_token}, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token(self):
        """Le logout doit blacklister le refresh token fourni."""
        response = self.client.post(
            self.logout_url,
            {"refresh": self.refresh_token},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}'
        )

        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        # Vérifie que ce refresh token est maintenant inutilisable
        retry_response = self.client.post(self.refresh_url, {"refresh": self.refresh_token}, format='json')
        self.assertEqual(retry_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_refresh_token_fails(self):
        """Un logout sans refresh token dans le body doit renvoyer une erreur 400."""
        response = self.client.post(
            self.logout_url,
            {},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_requires_authentication(self):
        """Le logout doit être refusé sans access token (401)."""
        response = self.client.post(self.logout_url, {"refresh": self.refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)