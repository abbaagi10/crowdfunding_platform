from functools import wraps
from rest_framework.response import Response
from rest_framework import status


def role_required(*allowed_roles):
    """
    Décorateur pour vues basées fonction (function-based views).
    Vérifie que request.user.role fait partie des rôles autorisés.

    Usage :
        @api_view(['GET'])
        @role_required('SUPERADMIN', 'USERADMIN')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)  # Préserve le nom et la docstring de la fonction originale (bonne pratique)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Authentification requise."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if request.user.role not in allowed_roles:
                return Response(
                    {"detail": "Vous n'avez pas les droits nécessaires pour cette action."},
                    status=status.HTTP_403_FORBIDDEN
                )

            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator