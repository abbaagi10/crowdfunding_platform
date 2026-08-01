from django.contrib.auth.tokens import PasswordResetTokenGenerator


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    Générateur de token pour l'activation de compte par email.
    Hérite de PasswordResetTokenGenerator car le mécanisme est identique :
    un token à usage unique, lié à un utilisateur, qui expire après usage.
    """

    def _make_hash_value(self, user, timestamp):
        """
        Détermine quelles informations rendent le token invalide une fois utilisées.
        Dès que is_email_verified passe à True, un ancien token généré
        avant activation devient automatiquement invalide.
        """
        return f"{user.pk}{timestamp}{user.is_email_verified}"


# Instance unique réutilisable dans tout le projet
account_activation_token = AccountActivationTokenGenerator()