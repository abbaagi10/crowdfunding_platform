from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.companies.models import CompanyProfile
from apps.projects.models import Category, Project

User = get_user_model()


class ProjectModelTests(TestCase):
    """
    Tests unitaires du modèle Project.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="project_owner@example.com", password="Pass123!", role=User.Role.ENTREPRISE
        )
        self.company = CompanyProfile.objects.create(
            user=self.user, company_name="Test SAS", registration_number="FR000111222"
        )
        self.category = Category.objects.create(name="Sante")

    def _make_project(self, **overrides):
        defaults = {
            'company': self.company,
            'category': self.category,
            'title': "Projet Test",
            'short_description': "Description courte",
            'full_description': "Description complete",
            'funding_goal': Decimal('10000.00'),
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=60),
        }
        defaults.update(overrides)
        return Project(**defaults)

    def test_project_created_with_default_draft_status(self):
        project = self._make_project()
        project.save()
        self.assertEqual(project.status, Project.Status.DRAFT)

    def test_slug_auto_generated_from_title(self):
        project = self._make_project(title="Mon Super Projet")
        project.save()
        self.assertEqual(project.slug, "mon-super-projet")

    def test_slug_unique_even_with_duplicate_titles(self):
        project1 = self._make_project(title="Meme Titre")
        project1.save()
        project2 = self._make_project(title="Meme Titre")
        project2.save()
        self.assertNotEqual(project1.slug, project2.slug)

    def test_end_date_before_start_date_raises_validation_error(self):
        project = self._make_project(
            start_date=date.today(),
            end_date=date.today() - timedelta(days=1)
        )
        with self.assertRaises(ValidationError):
            project.clean()

    def test_current_amount_exceeding_goal_raises_validation_error(self):
        project = self._make_project(funding_goal=Decimal('1000.00'))
        project.current_amount = Decimal('2000.00')
        with self.assertRaises(ValidationError):
            project.clean()

    def test_funding_percentage_calculation(self):
        project = self._make_project(funding_goal=Decimal('1000.00'))
        project.current_amount = Decimal('250.00')
        project.save()
        self.assertEqual(project.funding_percentage, Decimal('25.00'))

    def test_is_open_for_investment_true_when_active_and_not_expired(self):
        project = self._make_project(
            end_date=date.today() + timedelta(days=30)
        )
        project.status = Project.Status.ACTIVE
        project.save()
        self.assertTrue(project.is_open_for_investment)

    def test_is_open_for_investment_false_when_draft(self):
        project = self._make_project()
        project.save()
        self.assertFalse(project.is_open_for_investment)

    def test_is_open_for_investment_false_when_expired(self):
        project = self._make_project(
            start_date=date.today() - timedelta(days=100),
            end_date=date.today() - timedelta(days=1)
        )
        project.status = Project.Status.ACTIVE
        project.save()
        self.assertFalse(project.is_open_for_investment)

    def test_category_cannot_be_deleted_if_used_by_project(self):
        """on_delete=PROTECT doit empecher la suppression d'une categorie utilisee."""
        project = self._make_project()
        project.save()

        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.category.delete()
