from rest_framework import permissions

class IsCompanyProfileOwnerOrAdmin(permissions.BasePermission):
    """
    Permission pour vérifier que l'utilisateur est soit le propriétaire du profil,
    soit un administrateur.
    """
    def has_object_permission(self, request, view, obj):
        return (
            request.user == obj.user or
            request.user.role in ['SUPERADMIN', 'USERADMIN']
        )