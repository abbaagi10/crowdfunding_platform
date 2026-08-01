from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView, LogoutView, MeView, ActivateAccountView,
    CustomTokenObtainPairView, PasswordResetRequestView, PasswordResetConfirmView,
)
from .views import (
    RegisterView, LogoutView, MeView, ActivateAccountView,
    CustomTokenObtainPairView, PasswordResetRequestView, PasswordResetConfirmView,
    UserListView,
)

app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('login/refresh/', TokenRefreshView.as_view(), name='login_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', MeView.as_view(), name='me'),
    path('activate/<str:uidb64>/<str:token>/', ActivateAccountView.as_view(), name='activate'),

    # Réinitialisation de mot de passe
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('users/', UserListView.as_view(), name='user_list'),
]