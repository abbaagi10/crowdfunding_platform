from django.test import TestCase
from apps.accounts.models import CustomUser


class CustomUserModelTests(TestCase):
    """
    Tests unitaires du modèle CustomUser et de son manager.
    """

    def test_create_user_with_email_successful(self):
        """Un utilisateur normal doit pouvoir être créé avec un email et un mot de passe."""
        email = "investisseur@example.com"
        password = "TestPass123!"
        user = CustomUser.objects.create_user(email=email, password=password)

        self.assertEqual(user.email, email)
        # check_password vérifie le mot de passe HASHÉ, jamais en clair
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.role, CustomUser.Role.INVESTISSEUR)

    def test_email_is_normalized(self):
        """L'email doit être normalisé (partie domaine en minuscule)."""
        email = "test@EXAMPLE.COM"
        user = CustomUser.objects.create_user(email=email, password="TestPass123!")
        self.assertEqual(user.email, "test@example.com")

    def test_create_user_without_email_raises_error(self):
        """La création sans email doit lever une erreur explicite."""
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(email="", password="TestPass123!")

    def test_create_superuser_successful(self):
        """Un superuser doit avoir is_staff=True et is_superuser=True."""
        user = CustomUser.objects.create_superuser(
            email="admin@example.com",
            password="AdminPass123!"
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_user_string_representation(self):
        """__str__ doit retourner l'email et le rôle lisible."""
        user = CustomUser.objects.create_user(
            email="test@example.com",
            password="TestPass123!"
        )
        self.assertIn("test@example.com", str(user))