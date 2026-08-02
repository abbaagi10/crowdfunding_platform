from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import CompanyProfile
from apps.projects.models import Category, Project

User = get_user_model()


class ProjectListCreateViewTests(APITestCase):
    """
    Tests de l'endpoint /projects/ : liste filtrée par rôle + création.
    """

    def setUp(self):
        self.list_url = reverse('projects:project_list_create')
        self.category = Category.objects.create(name="Tech")

        self.company_user = User.objects.create_user(
            email="pv_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="PV SAS", registration_number="FR333444555"
        )

        self.other_company_user = User.objects.create_user(
            email="pv_other_company@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.other_company = CompanyProfile.objects.create(
            user=self.other_company_user, company_name="Other SAS", registration_number="FR666777888"
        )

        self.investor = User.objects.create_user(
            email="pv_investor@example.com", password="Pass123!",
            role=User.Role.INVESTISSEUR, is_email_verified=True
        )

        # Un projet DRAFT (privé) pour self.company
        self.draft_project = Project.objects.create(
            company=self.company, category=self.category, title="Draft Project",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('5000.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
        )

        # Un projet ACTIVE (public) pour other_company
        self.active_project = Project.objects.create(
            company=self.other_company, category=self.category, title="Active Project",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('5000.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
            status=Project.Status.ACTIVE,
        )

    def test_unauthenticated_sees_only_active_projects(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in response.data]
        self.assertIn("Active Project", titles)
        self.assertNotIn("Draft Project", titles)

    def test_investor_sees_only_active_projects(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.get(self.list_url)
        titles = [p['title'] for p in response.data]
        self.assertIn("Active Project", titles)
        self.assertNotIn("Draft Project", titles)

    def test_company_sees_only_its_own_projects_regardless_of_status(self):
        """L'entreprise proprietaire doit voir SON projet DRAFT, mais pas celui de l'autre entreprise."""
        self.client.force_authenticate(user=self.company_user)
        response = self.client.get(self.list_url)
        titles = [p['title'] for p in response.data]
        self.assertIn("Draft Project", titles)
        self.assertNotIn("Active Project", titles)

    def test_investor_cannot_create_project(self):
        self.client.force_authenticate(user=self.investor)
        response = self.client.post(self.list_url, {
            "category": self.category.id,
            "title": "Tentative Investisseur",
            "short_description": "desc",
            "full_description": "desc complete",
            "funding_goal": "1000.00",
            "start_date": str(timezone.now().date()),
            "end_date": str(timezone.now().date() + timedelta(days=30)),
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_can_create_project_with_draft_status(self):
        self.client.force_authenticate(user=self.company_user)
        response = self.client.post(self.list_url, {
            "category": self.category.id,
            "title": "Nouveau Projet",
            "short_description": "desc",
            "full_description": "desc complete",
            "funding_goal": "2000.00",
            "start_date": str(timezone.now().date()),
            "end_date": str(timezone.now().date() + timedelta(days=30)),
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], Project.Status.DRAFT)
        self.assertEqual(response.data['company'], self.company.id)

    def test_company_cannot_assign_project_to_another_company(self):
        """Meme si l'entreprise essaie de forcer 'company' dans la requete, cela doit etre ignore."""
        self.client.force_authenticate(user=self.company_user)
        response = self.client.post(self.list_url, {
            "company": self.other_company.id,  # Tentative de forcer une autre entreprise
            "category": self.category.id,
            "title": "Projet Frauduleux",
            "short_description": "desc",
            "full_description": "desc complete",
            "funding_goal": "2000.00",
            "start_date": str(timezone.now().date()),
            "end_date": str(timezone.now().date() + timedelta(days=30)),
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Le projet doit appartenir a l'entreprise CONNECTEE, pas celle forcee dans le payload
        self.assertEqual(response.data['company'], self.company.id)


class ProjectDetailViewTests(APITestCase):
    """
    Tests de l'endpoint /projects/<id>/ : lecture publique, ecriture protegee.
    """

    def setUp(self):
        self.category = Category.objects.create(name="Sante")

        self.owner_user = User.objects.create_user(
            email="dv_owner@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.owner_company = CompanyProfile.objects.create(
            user=self.owner_user, company_name="Owner SAS", registration_number="FR999000111"
        )

        self.other_user = User.objects.create_user(
            email="dv_other@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )

        self.superadmin = User.objects.create_user(
            email="dv_superadmin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )

        self.project = Project.objects.create(
            company=self.owner_company, category=self.category, title="Projet Detail",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('3000.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
        )
        self.detail_url = reverse('projects:project_detail', kwargs={'pk': self.project.pk})

    def test_anyone_can_read_project_detail(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_owner_can_update_own_project(self):
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.patch(self.detail_url, {"title": "Titre Modifie"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Titre Modifie")

    def test_other_company_cannot_update_someone_elses_project(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(self.detail_url, {"title": "Titre Pirate"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_any_project(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.patch(self.detail_url, {"title": "Titre Admin"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProjectSubmitForReviewViewTests(APITestCase):
    """
    Tests de l'endpoint /projects/<id>/submit/ : transition DRAFT -> PENDING.
    """

    def setUp(self):
        self.category = Category.objects.create(name="Culture")
        self.owner_user = User.objects.create_user(
            email="sv_owner@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.owner_company = CompanyProfile.objects.create(
            user=self.owner_user, company_name="Submit SAS", registration_number="FR222333444"
        )
        self.other_user = User.objects.create_user(
            email="sv_other@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )

        self.project = Project.objects.create(
            company=self.owner_company, category=self.category, title="Projet Submit",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('3000.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
        )
        self.submit_url = reverse('projects:project_submit', kwargs={'pk': self.project.pk})

    def test_owner_can_submit_draft_project(self):
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.post(self.submit_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Project.Status.PENDING)

    def test_cannot_submit_already_pending_project(self):
        self.project.status = Project.Status.PENDING
        self.project.save()

        self.client.force_authenticate(user=self.owner_user)
        response = self.client.post(self.submit_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_company_cannot_submit_someone_elses_project(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(self.submit_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ProjectModerationViewTests(APITestCase):
    """
    Tests de l'endpoint /projects/<id>/moderate/ : Valider/Refuser/Corriger.
    """

    def setUp(self):
        self.category = Category.objects.create(name="Environnement")
        self.owner_user = User.objects.create_user(
            email="mv_owner@example.com", password="Pass123!",
            role=User.Role.ENTREPRISE, is_email_verified=True
        )
        self.owner_company = CompanyProfile.objects.create(
            user=self.owner_user, company_name="Moderate SAS", registration_number="FR555666777"
        )
        self.superadmin = User.objects.create_user(
            email="mv_superadmin@example.com", password="Pass123!",
            role=User.Role.SUPERADMIN, is_email_verified=True
        )

        self.project = Project.objects.create(
            company=self.owner_company, category=self.category, title="Projet Moderate",
            short_description="desc", full_description="desc complete",
            funding_goal=Decimal('3000.00'),
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30),
            status=Project.Status.PENDING,
        )
        self.moderate_url = reverse('projects:project_moderate', kwargs={'pk': self.project.pk})

    def test_admin_approving_project_sets_status_to_active(self):
        """APPROVED doit automatiquement basculer le projet en ACTIVE (regle metier)."""
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.patch(self.moderate_url, {"status": "APPROVED"}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Project.Status.ACTIVE)

    def test_admin_rejecting_project_with_feedback(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.patch(self.moderate_url, {
            "status": "REJECTED",
            "admin_feedback": "Documentation insuffisante."
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Project.Status.REJECTED)

    def test_owner_cannot_moderate_own_project(self):
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.patch(self.moderate_url, {"status": "APPROVED"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_moderate_non_pending_project(self):
        self.project.status = Project.Status.DRAFT
        self.project.save()

        self.client.force_authenticate(user=self.superadmin)
        response = self.client.patch(self.moderate_url, {"status": "APPROVED"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_moderator_cannot_assign_draft_status(self):
        """validate_status() doit rejeter un statut hors du cadre de moderation."""
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.patch(self.moderate_url, {"status": "DRAFT"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

