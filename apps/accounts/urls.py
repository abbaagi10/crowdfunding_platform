from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import RegisterView, LogoutView, MeView

app_name = 'accounts'

urlpatterns = [
    # Inscription
    path('register/', RegisterView.as_view(), name='register'),

    # Connexion : fournie directement par simplejwt (email + password -> access + refresh)
    path('login/', TokenObtainPairView.as_view(), name='login'),

    # Rafraîchissement : envoie un refresh token, reçoit un nouvel access token
    path('login/refresh/', TokenRefreshView.as_view(), name='login_refresh'),

    # Déconnexion : blackliste le refresh token
    path('logout/', LogoutView.as_view(), name='logout'),

    # Profil de l'utilisateur connecté
    path('me/', MeView.as_view(), name='me'),
]