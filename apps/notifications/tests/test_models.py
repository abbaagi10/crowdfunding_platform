from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.notifications.models import Notification
from apps.notifications.tasks import create_notification

User = get_user_model()


class NotificationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="notif_model@example.com", password="Pass123!", role=User.Role.INVESTISSEUR
        )

    def test_notification_created_unread_by_default(self):
        notification = Notification.objects.create(
            user=self.user,
            notification_type=Notification.NotificationType.REPAYMENT_PAID,
            title="Test",
            message="Message de test",
        )
        self.assertFalse(notification.is_read)

    def test_string_representation(self):
        notification = Notification.objects.create(
            user=self.user,
            notification_type=Notification.NotificationType.INVESTMENT_RECEIVED,
            title="Test",
            message="Message de test",
        )
        self.assertIn("notif_model@example.com", str(notification))


class CreateNotificationTaskTests(TestCase):
    """
    Tests de la tache Celery create_notification.
    Grace a CELERY_TASK_ALWAYS_EAGER=True (settings de test), .delay()
    execute la tache immediatement et en synchrone -- on peut donc
    tester le resultat directement, sans mock ni worker reel.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="notif_task@example.com", password="Pass123!", role=User.Role.INVESTISSEUR
        )

    def test_task_creates_notification_in_database(self):
        create_notification.delay(
            user_id=self.user.pk,
            notification_type=Notification.NotificationType.KYC_APPROVED,
            title="KYC approuvé",
            message="Votre dossier a été validé.",
        )

        self.assertTrue(
            Notification.objects.filter(user=self.user, title="KYC approuvé").exists()
        )

    def test_task_with_nonexistent_user_id_does_not_raise(self):
        """
        Si l'utilisateur a ete supprime entre temps, la tache ne doit
        PAS planter -- elle doit juste ne rien faire silencieusement.
        """
        result = create_notification.delay(
            user_id=999999,
            notification_type=Notification.NotificationType.KYC_APPROVED,
            title="Test",
            message="Test",
        )
        # Ne leve aucune exception -- le test passe simplement si on arrive ici
        self.assertEqual(Notification.objects.filter(title="Test").count(), 0)
