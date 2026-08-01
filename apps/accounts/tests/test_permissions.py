from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, AnonymousUser
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from apps.accounts.permissions import (
    IsSuperAdmin, IsUserAdmin, IsAdminOrSuperAdmin, IsEntreprise, IsInvestisseur
)

User = get_user_model()


class PermissionClassesTests(TestCase):
    """
    Tests unitaires des classes de permission DRF personnalisées.
    """

    def setUp(self):
        self.factory = APIRequestFactory()

        self.superadmin = User.objects.create_user(
            email="superadmin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )
        self.useradmin = User.objects.create_user(
            email="useradmin@example.com", password="Pass123!",
            role=User.Role.USERADMIN, is_email_verified=True
        )
        self.entreprise = User.objects.create_user(
            email="entreprise@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.investisseur = User.objects.create_user(
            email="investisseur@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )

    def _make_request(self, user):
        request = self.factory.get('/fake-url/')
        request.user = user
        return request

    def test_is_superadmin_permission(self):
        permission = IsSuperAdmin()
        self.assertTrue(permission.has_permission(self._make_request(self.superadmin), None))
        self.assertFalse(permission.has_permission(self._make_request(self.useradmin), None))
        self.assertFalse(permission.has_permission(self._make_request(self.investisseur), None))

    def test_is_useradmin_permission(self):
        permission = IsUserAdmin()
        self.assertTrue(permission.has_permission(self._make_request(self.useradmin), None))
        self.assertFalse(permission.has_permission(self._make_request(self.superadmin), None))

    def test_is_admin_or_superadmin_permission(self):
        permission = IsAdminOrSuperAdmin()
        self.assertTrue(permission.has_permission(self._make_request(self.superadmin), None))
        self.assertTrue(permission.has_permission(self._make_request(self.useradmin), None))
        self.assertFalse(permission.has_permission(self._make_request(self.entreprise), None))
        self.assertFalse(permission.has_permission(self._make_request(self.investisseur), None))

    def test_is_entreprise_permission(self):
        permission = IsEntreprise()
        self.assertTrue(permission.has_permission(self._make_request(self.entreprise), None))
        self.assertFalse(permission.has_permission(self._make_request(self.investisseur), None))

    def test_is_investisseur_permission(self):
        permission = IsInvestisseur()
        self.assertTrue(permission.has_permission(self._make_request(self.investisseur), None))
        self.assertFalse(permission.has_permission(self._make_request(self.entreprise), None))

    def test_unauthenticated_user_denied_all_permissions(self):
        anonymous = AnonymousUser()

        for permission_class in (IsSuperAdmin, IsUserAdmin, IsAdminOrSuperAdmin, IsEntreprise, IsInvestisseur):
            permission = permission_class()
            self.assertFalse(permission.has_permission(self._make_request(anonymous), None))


class RoleGroupSyncTests(TestCase):
    """
    Tests de la synchronisation automatique Role <-> Group via signal.
    """

    def test_user_creation_creates_and_assigns_group(self):
        user = User.objects.create_user(
            email="groupetest@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR
        )
        self.assertTrue(Group.objects.filter(name=User.Role.INVESTISSEUR).exists())
        self.assertTrue(user.groups.filter(name=User.Role.INVESTISSEUR).exists())

    def test_role_change_updates_group_membership(self):
        user = User.objects.create_user(
            email="rolechange@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR
        )
        self.assertTrue(user.groups.filter(name=User.Role.INVESTISSEUR).exists())

        user.role = User.Role.ENTREPRISE
        user.save()

        self.assertFalse(user.groups.filter(name=User.Role.INVESTISSEUR).exists())
        self.assertTrue(user.groups.filter(name=User.Role.ENTREPRISE).exists())

    def test_user_never_belongs_to_multiple_role_groups(self):
        user = User.objects.create_user(
            email="singlerole@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN
        )
        role_group_names = [choice[0] for choice in User.Role.choices]
        user_role_groups = user.groups.filter(name__in=role_group_names)
        self.assertEqual(user_role_groups.count(), 1)


class UserListViewTests(APITestCase):
    """
    Tests d'intégration de l'endpoint /api/v1/accounts/users/,
    protégé par la permission IsAdminOrSuperAdmin.
    """

    def setUp(self):
        self.users_url = reverse('accounts:user_list')

        self.superadmin = User.objects.create_user(
            email="listtest_superadmin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )
        self.useradmin = User.objects.create_user(
            email="listtest_useradmin@example.com", password="Pass123!",
            role=User.Role.USERADMIN, is_email_verified=True
        )
        self.investisseur = User.objects.create_user(
            email="listtest_investisseur@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )
        self.entreprise = User.objects.create_user(
            email="listtest_entreprise@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )

    def test_superadmin_can_list_users(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_useradmin_can_list_users(self):
        self.client.force_authenticate(user=self.useradmin)
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_investisseur_cannot_list_users(self):
        self.client.force_authenticate(user=self.investisseur)
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_entreprise_cannot_list_users(self):
        self.client.force_authenticate(user=self.entreprise)
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_list_users(self):
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
