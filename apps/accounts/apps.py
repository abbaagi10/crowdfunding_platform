from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'

    def ready(self):
        """
        Méthode appelée par Django au démarrage de l'application.
        On y importe signals.py pour que les @receiver soient bien enregistrés.
        """
        import apps.accounts.signals  # noqa: F401