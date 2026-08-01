from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import account_activation_token


def send_activation_email(user, request=None):
    """
    Envoie un email contenant un lien d'activation unique pour le compte donné.
    """
    # Encode l'ID utilisateur en base64 URL-safe (évite les caractères spéciaux dans l'URL)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    # Génère un token unique lié à cet utilisateur et à son état actuel
    token = account_activation_token.make_token(user)

    # Construit le lien complet vers le frontend, qui appellera ensuite l'API
    activation_link = f"{settings.FRONTEND_URL}/activate/{uid}/{token}/"

    subject = "Activez votre compte Crowdfunding Platform"
    message = (
        f"Bonjour {user.first_name or user.email},\n\n"
        f"Merci de vous être inscrit sur notre plateforme.\n"
        f"Veuillez cliquer sur le lien suivant pour activer votre compte :\n\n"
        f"{activation_link}\n\n"
        f"Ce lien est à usage unique.\n\n"
        f"L'équipe Crowdfunding Platform"
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@crowdfunding.com',
        [user.email],
        fail_silently=False,
    )