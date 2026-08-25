from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    """
    Modèle de notification in-app.
    """
    
    class Type(models.TextChoices):
        INFO = 'INFO', 'Information'
        SUCCESS = 'SUCCESS', 'Succès'
        WARNING = 'WARNING', 'Avertissement'
        ERROR = 'ERROR', 'Erreur'
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Destinataire"
    )
    
    notification_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.INFO,
        verbose_name="Type de notification"
    )
    
    title = models.CharField(max_length=255, verbose_name="Titre")
    message = models.TextField(verbose_name="Message")
    data = models.JSONField(default=dict, blank=True, verbose_name="Données supplémentaires")
    
    is_read = models.BooleanField(default=False, verbose_name="Lue")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Date de lecture")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
    
    def __str__(self):
        return f"{self.title} - {self.recipient.email}"
    
    def mark_as_read(self):
        """Marque la notification comme lue."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()