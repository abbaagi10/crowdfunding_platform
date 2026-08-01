from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.accounts.permissions import (
    IsSuperAdmin, IsUserAdmin, IsAdminOrSuperAdmin, IsEntreprise, IsInvestisseur
)

User = get_user_model()


class PermissionClassesTests(TestCase):
    """
    Tests unitaires des classes de permission DRF personnalisées.
    On utilise APIRequestFactory pour construire des requêtes factices,
    sans avoir besoin de vraies URLs/vues.
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
        from django.contrib.auth.models import AnonymousUser
        anonymous = AnonymousUser()

        for permission_class in (IsSuperAdmin, IsUserAdmin, IsAdminOrSuperAdmin, IsEntreprise, IsInvestisseur):
            permission = permission_class()
            self.assertFalse(permission.has_permission(self._make_request(anonymous), None))


class RoleGroupSyncTests(TestCase):
    """
    Tests de la synchronisation automatique Role <-> Group via signal.
    """

    def test_user_creation_creates_and_assigns_group(self):
        """La création d'un utilisateur doit créer le Group correspondant et l'y assigner."""
        user = User.objects.create_user(
            email="groupetest@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR
        )

        self.assertTrue(Group.objects.filter(name=User.Role.INVESTISSEUR).exists())
        self.assertTrue(user.groups.filter(name=User.Role.INVESTISSEUR).exists())

    def test_role_change_updates_group_membership(self):
        """Changer le rôle d'un utilisateur doit mettre à jour son Group automatiquement."""
        user = User.objects.create_user(
            email="rolechange@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR
        )
        self.assertTrue(user.groups.filter(name=User.Role.INVESTISSEUR).exists())

        # Changement de rôle
        user.role = User.Role.ENTREPRISE
        user.save()

        # L'ancien groupe ne doit plus être assigné, le nouveau doit l'être
        self.assertFalse(user.groups.filter(name=User.Role.INVESTISSEUR).exists())
        self.assertTrue(user.groups.filter(name=User.Role.ENTREPRISE).exists())

    def test_user_never_belongs_to_multiple_role_groups(self):
        """Un utilisateur ne doit jamais appartenir à plusieurs groupes de rôle simultanément."""
        user = User.objects.create_user(
            email="singlerole@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN
        )

        role_group_names = [choice[0] for choice in User.Role.choices]
        user_role_groups = user.groups.filter(name__in=role_group_names)

        self.assertEqual(user_role_groups.count(), 1)