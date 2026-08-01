from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import CompanyProfile

User = get_user_model()


class MyCompanyProfileViewTests(APITestCase):
    """
    Tests de l'endpoint /profile/me/ : consultation et modification
    de son propre profil entreprise.
    """

    def setUp(self):
        self.me_url = reverse('companies:my_profile')
        self.company_user = User.objects.create_user(
            email="mycompany@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )

    def test_profile_auto_created_with_temporary_values(self):
        """Le profil doit être créé automatiquement avec des valeurs temporaires au premier accès."""
        self.client.force_authenticate(user=self.company_user)
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(CompanyProfile.objects.filter(user=self.company_user).exists())
        self.assertIn("TEMP-", response.data['registration_number'])

    def test_unauthenticated_cannot_access_profile(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_update_own_profile_fields(self):
        """L'entreprise doit pouvoir modifier ses propres champs KYB."""
        self.client.force_authenticate(user=self.company_user)
        response = self.client.patch(self.me_url, {
            "company_name": "Ma Vraie Entreprise SAS",
            "registration_number": "FR999888777"
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['company_name'], "Ma Vraie Entreprise SAS")

    def test_user_cannot_change_own_verification_status(self):
        """L'entreprise ne doit JAMAIS pouvoir changer son propre verification_status."""
        self.client.force_authenticate(user=self.company_user)
        response = self.client.patch(self.me_url, {
            "verification_status": "APPROVED"
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['verification_status'], CompanyProfile.VerificationStatus.PENDING)


class CompanyProfileListViewTests(APITestCase):
    """
    Tests de l'endpoint /profiles/ : liste réservée à l'administration.
    """

    def setUp(self):
        self.list_url = reverse('companies:profile_list')

        self.superadmin = User.objects.create_user(
            email="listview_superadmin_c@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )
        self.company_user = User.objects.create_user(
            email="listview_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        CompanyProfile.objects.create(
            user=self.company_user, company_name="Test SAS", registration_number="FR111222333"
        )

    def test_admin_can_list_all_profiles(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_company_cannot_list_all_profiles(self):
        self.client.force_authenticate(user=self.company_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CompanyProfileDetailViewTests(APITestCase):
    """
    Tests de l'endpoint /profiles/<id>/ : accès protégé au niveau OBJET.
    """

    def setUp(self):
        self.owner = User.objects.create_user(
            email="detail_owner_c@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.other_user = User.objects.create_user(
            email="detail_other_c@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.superadmin = User.objects.create_user(
            email="detail_superadmin_c@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )

        self.profile = CompanyProfile.objects.create(
            user=self.owner, company_name="Owner SAS", registration_number="FR444555666"
        )
        self.detail_url = reverse('companies:profile_detail', kwargs={'pk': self.profile.pk})

    def test_owner_can_access_own_profile_detail(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_company_cannot_access_someone_elses_profile(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_access_any_profile_detail(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CompanyProfileVerificationViewTests(APITestCase):
    """
    Tests de l'endpoint /profiles/<id>/verify/ : validation KYB par l'administration.
    """

    def setUp(self):
        self.company_user = User.objects.create_user(
            email="verify_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.superadmin = User.objects.create_user(
            email="verify_superadmin_c@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )

        self.profile = CompanyProfile.objects.create(
            user=self.company_user, company_name="Verify SAS", registration_number="FR777888999"
        )
        self.verify_url = reverse('companies:profile_verify', kwargs={'pk': self.profile.pk})

    def test_admin_can_approve_kyb(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.patch(self.verify_url, {
            "verification_status": "APPROVED"
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.verification_status, CompanyProfile.VerificationStatus.APPROVED)

    def test_admin_can_reject_kyb_with_reason(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.patch(self.verify_url, {
            "verification_status": "REJECTED",
            "rejection_reason": "Documents manquants."
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.verification_status, CompanyProfile.VerificationStatus.REJECTED)
        self.assertEqual(self.profile.rejection_reason, "Documents manquants.")

    def test_company_cannot_verify_own_kyb(self):
        self.client.force_authenticate(user=self.company_user)
        response = self.client.patch(self.verify_url, {
            "verification_status": "APPROVED"
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
