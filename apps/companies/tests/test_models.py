from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.companies.models import CompanyProfile

User = get_user_model()


class CompanyProfileModelTests(TestCase):
    """
    Tests unitaires du modèle CompanyProfile.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="company_model_test@example.com",
            password="Pass123!",
            role=User.Role.ENTREPRISE
        )

    def test_profile_created_with_default_pending_status(self):
        """Un profil nouvellement créé doit avoir le statut PENDING par défaut."""
        profile = CompanyProfile.objects.create(
            user=self.user,
            company_name="Test SAS",
            registration_number="FR000000001"
        )
        self.assertEqual(profile.verification_status, CompanyProfile.VerificationStatus.PENDING)

    def test_one_to_one_constraint_prevents_duplicate_profiles(self):
        """Un utilisateur ne peut avoir qu'UN SEUL profil entreprise."""
        CompanyProfile.objects.create(
            user=self.user, company_name="Test SAS", registration_number="FR000000002"
        )
        with self.assertRaises(Exception):
            CompanyProfile.objects.create(
                user=self.user, company_name="Autre SAS", registration_number="FR000000003"
            )

    def test_registration_number_must_be_unique(self):
        """Deux entreprises ne peuvent pas partager le même numéro d'enregistrement."""
        other_user = User.objects.create_user(
            email="other_company@example.com", password="Pass123!", role=User.Role.ENTREPRISE
        )
        CompanyProfile.objects.create(
            user=self.user, company_name="Test SAS", registration_number="FR000000004"
        )
        with self.assertRaises(Exception):
            CompanyProfile.objects.create(
                user=other_user, company_name="Autre SAS", registration_number="FR000000004"
            )

    def test_is_kyb_complete_false_when_documents_missing(self):
        """is_kyb_complete doit être False tant que les documents essentiels manquent."""
        profile = CompanyProfile.objects.create(
            user=self.user, company_name="Test SAS", registration_number="FR000000005",
            legal_representative_name="Jean Dupont", iban="FR7630006000011234567890189"
        )
        self.assertFalse(profile.is_kyb_complete)

    def test_invalid_iban_format_rejected(self):
        """Un IBAN mal formaté doit échouer à la validation."""
        profile = CompanyProfile(
            user=self.user, company_name="Test SAS", registration_number="FR000000006",
            iban="INVALID_IBAN"
        )
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_string_representation(self):
        """__str__ doit contenir le nom de l'entreprise et le statut lisible."""
        profile = CompanyProfile.objects.create(
            user=self.user, company_name="Test SAS", registration_number="FR000000007"
        )
        self.assertIn("Test SAS", str(profile))
