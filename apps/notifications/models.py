from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    Notification IN-APP persistante (visible dans une interface type "cloche").
    Trace metier durable, independante du canal d'envoi reel (email, push...).
    """

    class NotificationType(models.TextChoices):
        ACCOUNT_ACTIVATED = 'ACCOUNT_ACTIVATED', 'Compte active'
        KYC_APPROVED = 'KYC_APPROVED', 'KYC approuve'
        KYC_REJECTED = 'KYC_REJECTED', 'KYC rejete'
        KYB_APPROVED = 'KYB_APPROVED', 'KYB approuve'
        KYB_REJECTED = 'KYB_REJECTED', 'KYB rejete'
        PROJECT_SUBMITTED = 'PROJECT_SUBMITTED', 'Projet soumis'
        PROJECT_APPROVED = 'PROJECT_APPROVED', 'Projet approuve'
        PROJECT_REJECTED = 'PROJECT_REJECTED', 'Projet refuse'
        PROJECT_NEEDS_CORRECTION = 'PROJECT_NEEDS_CORRECTION', 'Corrections demandees'
        INVESTMENT_RECEIVED = 'INVESTMENT_RECEIVED', 'Investissement recu'
        REPAYMENT_PAID = 'REPAYMENT_PAID', 'Echeance payee'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Destinataire"
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        verbose_name="Type"
    )

    title = models.CharField(max_length=255, verbose_name="Titre")
    message = models.TextField(verbose_name="Message")

    is_read = models.BooleanField(default=False, verbose_name="Lue")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        indexes = [
            # Acceleration de "mes notifications non lues, les plus recentes d'abord"
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.user.email}"
