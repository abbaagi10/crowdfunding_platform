from rest_framework.permissions import BasePermission


class IsProfileOwnerOrAdmin(BasePermission):
    """
    Permission au niveau OBJET : autorise uniquement le propriétaire
    du profil (obj.user == request.user) ou un membre de l'administration.

    Utilisée sur les actions retrieve/update/delete d'un InvestorProfile précis,
    jamais sur un simple 'list' (qui a sa propre logique de filtrage, voir views.py).
    """
    message = "Vous ne pouvez accéder qu'à votre propre profil."

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Un admin peut toujours accéder à n'importe quel profil
        if request.user.role in (request.user.Role.USERADMIN, request.user.Role.SUPERADMIN):
            return True

        # Sinon, uniquement le propriétaire du profil
        return obj.user == request.user