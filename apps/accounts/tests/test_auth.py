from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RegisterTests(APITestCase):
    def setUp(self):
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
        response = self.client.post(self.register_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_register_password_mismatch(self):
        payload = self.valid_payload.copy()
        payload['password2'] = "DifferentPass123!"
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_register_duplicate_email(self):
        self.client.post(self.register_url, self.valid_payload, format='json')
        response = self.client.post(self.register_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_register_weak_password_rejected(self):
        payload = self.valid_payload.copy()
        payload['password'] = "12345678"
        payload['password2'] = "12345678"
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    def setUp(self):
        self.login_url = reverse('accounts:login')
        self.user = User.objects.create_user(
            email="logintest@example.com",
            password="StrongPass123!",
            is_email_verified=True
        )

    def test_login_success(self):
        response = self.client.post(self.login_url, {
            "email": "logintest@example.com",
            "password": "StrongPass123!"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_wrong_password(self):
        response = self.client.post(self.login_url, {
            "email": "logintest@example.com",
            "password": "WrongPassword!"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_email(self):
        response = self.client.post(self.login_url, {
            "email": "doesnotexist@example.com",
            "password": "StrongPass123!"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MeEndpointTests(APITestCase):
    def setUp(self):
        self.me_url = reverse('accounts:me')
        self.user = User.objects.create_user(
            email="metest@example.com",
            password="StrongPass123!"
        )

    def test_me_requires_authentication(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_with_valid_token(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], "metest@example.com")


class RefreshAndLogoutTests(APITestCase):
    def setUp(self):
        self.login_url = reverse('accounts:login')
        self.refresh_url = reverse('accounts:login_refresh')
        self.logout_url = reverse('accounts:logout')

        self.user = User.objects.create_user(
            email="tokentest@example.com",
            password="StrongPass123!",
            is_email_verified=True
        )

        login_response = self.client.post(self.login_url, {
            "email": "tokentest@example.com",
            "password": "StrongPass123!"
        }, format='json')

        self.access_token = login_response.data['access']
        self.refresh_token = login_response.data['refresh']

    def test_refresh_rotates_token(self):
        response = self.client.post(self.refresh_url, {"refresh": self.refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertNotEqual(response.data['refresh'], self.refresh_token)

    def test_old_refresh_token_is_blacklisted_after_rotation(self):
        self.client.post(self.refresh_url, {"refresh": self.refresh_token}, format='json')
        response = self.client.post(self.refresh_url, {"refresh": self.refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token(self):
        response = self.client.post(
            self.logout_url,
            {"refresh": self.refresh_token},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}'
        )
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        retry_response = self.client.post(self.refresh_url, {"refresh": self.refresh_token}, format='json')
        self.assertEqual(retry_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_refresh_token_fails(self):
        response = self.client.post(
            self.logout_url, {}, format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_requires_authentication(self):
        response = self.client.post(self.logout_url, {"refresh": self.refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
