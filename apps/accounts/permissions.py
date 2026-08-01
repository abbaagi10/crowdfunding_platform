from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """
    Autorise uniquement les utilisateurs ayant le rôle SUPERADMIN.
    """
    message = "Seul un Super Administrateur peut effectuer cette action."

    def has_permission(self, request, view):
        # request.user existe toujours (AnonymousUser si non connecté),
        # donc on vérifie explicitement is_authenticated avant d'accéder à .role
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == request.user.Role.SUPERADMIN
        )


class IsUserAdmin(BasePermission):
    """
    Autorise uniquement les utilisateurs ayant le rôle USERADMIN.
    """
    message = "Seul un Administrateur peut effectuer cette action."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == request.user.Role.USERADMIN
        )


class IsAdminOrSuperAdmin(BasePermission):
    """
    Autorise les UserAdmin ET les SuperAdmin.
    Utile pour les actions de modération (valider/refuser un projet, par exemple),
    qui doivent être accessibles aux deux niveaux d'administration.
    """
    message = "Seul un membre de l'équipe d'administration peut effectuer cette action."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in (request.user.Role.USERADMIN, request.user.Role.SUPERADMIN)
        )


class IsEntreprise(BasePermission):
    """
    Autorise uniquement les utilisateurs ayant le rôle ENTREPRISE.
    """
    message = "Seule une Entreprise peut effectuer cette action."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == request.user.Role.ENTREPRISE
        )


class IsInvestisseur(BasePermission):
    """
    Autorise uniquement les utilisateurs ayant le rôle INVESTISSEUR.
    """
    message = "Seul un Investisseur peut effectuer cette action."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == request.user.Role.INVESTISSEUR
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Autorise le PROPRIÉTAIRE d'un objet, ou un membre de l'administration.
    Nécessite que l'objet possède un attribut 'user' ou 'owner' (à adapter
    selon le modèle réel utilisé dans les étapes futures : Project, InvestorProfile, etc.)

    Cette permission est une PERMISSION AU NIVEAU OBJET (has_object_permission),
    contrairement aux précédentes qui sont des permissions au niveau VUE (has_permission).
    Elle est vérifiée APRÈS que has_permission ait déjà autorisé la requête,
    et seulement pour les actions sur un objet précis (retrieve, update, delete).
    """
    message = "Vous n'êtes pas autorisé à accéder à cette ressource."

    def has_object_permission(self, request, view, obj):
        if request.user.role in (request.user.Role.USERADMIN, request.user.Role.SUPERADMIN):
            return True

        # Supporte soit un attribut 'user', soit 'owner', selon le modèle
        owner = getattr(obj, 'user', None) or getattr(obj, 'owner', None)
        return owner == request.user