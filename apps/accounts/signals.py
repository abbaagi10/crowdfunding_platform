from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group

from .models import CustomUser
from .utils import send_activation_email


@receiver(post_save, sender=CustomUser)
def send_activation_email_on_creation(sender, instance, created, **kwargs):
    """
    Envoie un email d'activation lors de la création initiale d'un compte
    (déjà existant depuis la sous-étape 2.3, inchangé).
    """
    if created and not instance.is_superuser:
        send_activation_email(instance)


@receiver(post_save, sender=CustomUser)
def sync_user_group_with_role(sender, instance, **kwargs):
    """
    Synchronise automatiquement l'appartenance aux Groups Django
    avec le champ 'role' de l'utilisateur, à CHAQUE sauvegarde
    (création OU modification).

    Exemple : si un USERADMIN change le rôle d'un utilisateur
    de INVESTISSEUR à ENTREPRISE via l'admin, ce signal retire
    automatiquement l'utilisateur du groupe "INVESTISSEUR" et
    l'ajoute au groupe "ENTREPRISE".
    """
    # get_or_create évite une erreur si le groupe n'existe pas encore
    # (utile surtout au tout premier lancement du projet)
    group, _ = Group.objects.get_or_create(name=instance.role)

    # On retire l'utilisateur de tous les AUTRES groupes de rôle,
    # pour éviter qu'il cumule plusieurs rôles à la fois par erreur
    role_group_names = [choice[0] for choice in CustomUser.Role.choices]
    instance.groups.remove(
        *Group.objects.filter(name__in=role_group_names).exclude(name=instance.role)
    )

    # Puis on l'ajoute au groupe correspondant à son rôle actuel
    instance.groups.add(group)