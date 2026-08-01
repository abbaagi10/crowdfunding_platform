from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.investors.models import InvestorProfile

User = get_user_model()


class MyInvestorProfileViewTests(APITestCase):
    def setUp(self):
        self.me_url = reverse('investors:my_profile')
        self.investor = User.objects.create_user(
            email="myprofile@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.other_investor = User.objects.create_user(
            email="otherinvestor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )

    def test_profile_auto_created_on_first_access(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(InvestorProfile.objects.filter(user=self.investor).exists())

    def test_unauthenticated_cannot_access_profile(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_update_own_profile_fields(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.patch(self.me_url, {
            "nationality": "Française",
            "phone_number": "+33612345678"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nationality'], "Française")

    def test_user_cannot_change_own_verification_status(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.patch(self.me_url, {
            "verification_status": "APPROVED"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['verification_status'], InvestorProfile.VerificationStatus.PENDING)

    def test_each_user_sees_only_their_own_profile_via_me_endpoint(self):
        self.client.force_authenticate(user=self.investor)
        response1 = self.client.get(self.me_url)

        self.client.force_authenticate(user=self.other_investor)
        response2 = self.client.get(self.me_url)

        self.assertNotEqual(response1.data['id'], response2.data['id'])


class InvestorProfileListViewTests(APITestCase):
    def setUp(self):
        self.list_url = reverse('investors:profile_list')
        self.superadmin = User.objects.create_user(
            email="listview_superadmin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )
        self.investor = User.objects.create_user(
            email="listview_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        InvestorProfile.objects.create(user=self.investor)

    def test_admin_can_list_all_profiles(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_investor_cannot_list_all_profiles(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class InvestorProfileDetailViewTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="detail_owner@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.other_user = User.objects.create_user(
            email="detail_other@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.superadmin = User.objects.create_user(
            email="detail_superadmin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )
        self.profile = InvestorProfile.objects.create(user=self.owner)
        self.detail_url = reverse('investors:profile_detail', kwargs={'pk': self.profile.pk})

    def test_owner_can_access_own_profile_detail(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_user_cannot_access_someone_elses_profile(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_access_any_profile_detail(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class InvestorProfileVerificationViewTests(APITestCase):
    def setUp(self):
        self.investor = User.objects.create_user(
            email="verify_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.superadmin = User.objects.create_user(
            email="verify_superadmin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )
        self.profile = InvestorProfile.objects.create(user=self.investor)
        self.verify_url = reverse('investors:profile_verify', kwargs={'pk': self.profile.pk})

    def test_admin_can_approve_kyc(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.patch(self.verify_url, {
            "verification_status": "APPROVED"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.verification_status, InvestorProfile.VerificationStatus.APPROVED)

    def test_admin_can_reject_kyc_with_reason(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.patch(self.verify_url, {
            "verification_status": "REJECTED",
            "rejection_reason": "Document illisible."
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.verification_status, InvestorProfile.VerificationStatus.REJECTED)
        self.assertEqual(self.profile.rejection_reason, "Document illisible.")

    def test_investor_cannot_verify_own_kyc(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.patch(self.verify_url, {
            "verification_status": "APPROVED"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
