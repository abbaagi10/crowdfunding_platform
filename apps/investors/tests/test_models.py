from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.investors.models import InvestorProfile

User = get_user_model()


class InvestorProfileModelTests(TestCase):
    """
    Tests unitaires du modèle InvestorProfile.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="investor_model_test@example.com",
            password="Pass123!",
            role=User.Role.INVESTISSEUR
        )

    def test_profile_created_with_default_pending_status(self):
        profile = InvestorProfile.objects.create(user=self.user)
        self.assertEqual(profile.verification_status, InvestorProfile.VerificationStatus.PENDING)

    def test_one_to_one_constraint_prevents_duplicate_profiles(self):
        InvestorProfile.objects.create(user=self.user)

        with self.assertRaises(Exception):
            InvestorProfile.objects.create(user=self.user)

    def test_is_kyc_complete_false_when_documents_missing(self):
        profile = InvestorProfile.objects.create(user=self.user, nationality="Française")
        self.assertFalse(profile.is_kyc_complete)

    def test_string_representation(self):
        profile = InvestorProfile.objects.create(user=self.user)
        self.assertIn("investor_model_test@example.com", str(profile))
