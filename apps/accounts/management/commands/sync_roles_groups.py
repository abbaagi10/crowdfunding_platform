from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

from apps.accounts.models import CustomUser


class Command(BaseCommand):
    """
    Commande personnalisée : python manage.py sync_roles_groups

    Crée les 4 Groups Django correspondant aux rôles définis
    dans CustomUser.Role, s'ils n'existent pas déjà.
    Utile à exécuter une fois après le déploiement initial,
    ou après un ajout de nouveau rôle dans le modèle.
    """
    help = "Crée les Groups Django correspondant aux rôles définis dans CustomUser.Role."

    def handle(self, *args, **options):
        for role_value, role_label in CustomUser.Role.choices:
            group, created = Group.objects.get_or_create(name=role_value)
            if created:
                self.stdout.write(self.style.SUCCESS(f"✓ Groupe créé : {role_value} ({role_label})"))
            else:
                self.stdout.write(f"— Groupe déjà existant : {role_value} ({role_label})")

        self.stdout.write(self.style.SUCCESS("Synchronisation terminée."))