from rest_framework.permissions import BasePermission


class IsCompanyProfileOwnerOrAdmin(BasePermission):
    """
    Permission au niveau OBJET : autorise uniquement le propriétaire
    du profil entreprise ou un membre de l'administration.
    """
    message = "Vous ne pouvez accéder qu'au profil de votre propre entreprise."

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        if request.user.role in (request.user.Role.USERADMIN, request.user.Role.SUPERADMIN):
            return True

        return obj.user == request.user
