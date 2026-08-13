from celery import shared_task
from django.contrib.auth import get_user_model

from .models import Notification

User = get_user_model()


@shared_task
def create_notification(user_id, notification_type, title, message):
    """
    Tache Celery generique : cree une Notification en base pour un utilisateur.

    Prend des IDENTIFIANTS SIMPLES (user_id, pas un objet User) en parametres,
    jamais des objets Django complexes -- une tache Celery serialise ses
    arguments (JSON, voir CELERY_TASK_SERIALIZER), et un objet ORM ne se
    serialise pas correctement. C'est une regle Celery fondamentale :
    toujours passer des types simples (int, str, Decimal en str...), jamais
    des instances de modeles.
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        # L'utilisateur a pu etre supprime entre l'appel .delay() et l'execution
        # reelle de la tache -- on ignore silencieusement plutot que de planter.
        return

    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
    )


@shared_task
def send_activation_email_task(user_id):
    """
    Version asynchrone de send_activation_email (Etape 2), qui tournait
    jusqu'ici en SYNCHRONE dans le signal post_save de CustomUser --
    bloquant potentiellement l'inscription si l'envoi d'email est lent.
    """
    from apps.accounts.utils import send_activation_email

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    send_activation_email(user)
