from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsProjectOwnerOrAdminOrReadOnly(BasePermission):
    """
    Permission au niveau OBJET pour les projets :
    - Lecture (GET) : autorisée pour tout utilisateur authentifié
      (les investisseurs doivent pouvoir consulter les projets ACTIFS).
    - Écriture (PUT/PATCH/DELETE) : réservée au PROPRIÉTAIRE du projet
      (l'entreprise qui l'a créé) ou à l'administration.
    """
    message = "Seule l'entreprise porteuse du projet ou un administrateur peut modifier ce projet."

    def has_object_permission(self, request, view, obj):
        # SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS') : toujours autorisées en lecture
        if request.method in SAFE_METHODS:
            return True

        if not request.user.is_authenticated:
            return False

        if request.user.role in (request.user.Role.USERADMIN, request.user.Role.SUPERADMIN):
            return True

        # obj.company.user : remonte du Project -> CompanyProfile -> CustomUser
        return obj.company.user == request.user


class IsEntrepriseRole(BasePermission):
    """
    Autorise uniquement les utilisateurs ayant le rôle ENTREPRISE.
    Utilisé pour la création de projets (has_permission, niveau vue) :
    seule une entreprise peut créer un NOUVEAU projet, avant même
    de savoir de quel projet précis il s'agit.
    """
    message = "Seule une Entreprise peut créer un projet."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == request.user.Role.ENTREPRISE
        )
