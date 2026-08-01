from django.contrib.auth import get_user_model
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView

from .serializers import RegisterSerializer, UserSerializer, CustomTokenObtainPairSerializer
from .tokens import account_activation_token
from django.core.mail import send_mail
from django.conf import settings
from .serializers import (
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    password_reset_token,
)
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    Endpoint d'inscription (POST /api/v1/accounts/register/).
    Crée un utilisateur et retourne directement une paire de tokens JWT (auto-login).
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

    # AllowAny : l'inscription doit être accessible sans authentification préalable
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Génère immédiatement une paire de tokens pour le nouvel utilisateur
        refresh = RefreshToken.for_user(user)

        return Response({
            "user": UserSerializer(user).data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(BaseTokenObtainPairView):
    """
    Vue de connexion personnalisée (POST /api/v1/accounts/login/).
    Utilise CustomTokenObtainPairSerializer, qui vérifie en plus
    que le compte a bien été activé (is_email_verified=True)
    avant d'autoriser la connexion.
    """
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """
    Endpoint de déconnexion (POST /api/v1/accounts/logout/).
    Ajoute le refresh token fourni à la blacklist, le rendant inutilisable.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"detail": "Le refresh token est requis."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            # blacklist() ajoute ce token à la table token_blacklist
            token.blacklist()

            return Response(
                {"detail": "Déconnexion réussie."},
                status=status.HTTP_205_RESET_CONTENT
            )
        except TokenError:
            return Response(
                {"detail": "Token invalide ou déjà expiré."},
                status=status.HTTP_400_BAD_REQUEST
            )


class MeView(APIView):
    """
    Endpoint de profil (GET /api/v1/accounts/me/).
    Retourne les informations de l'utilisateur actuellement authentifié.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class ActivateAccountView(APIView):
    """
    Endpoint d'activation de compte (GET /api/v1/accounts/activate/<uidb64>/<token>/).
    Active le compte d'un utilisateur à partir du lien reçu par email.
    """
    permission_classes = (AllowAny,)

    def get(self, request, uidb64, token):
        try:
            # Décode l'ID utilisateur depuis l'URL (encodé en base64 URL-safe)
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            # uid invalide, non décodable, ou utilisateur inexistant -> réponse générique
            return Response(
                {"detail": "Lien d'activation invalide ou expiré."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # IMPORTANT : on vérifie D'ABORD si le compte est déjà activé,
        # AVANT de valider le token. En effet, le token inclut is_email_verified
        # dans son hash (voir tokens.py) : il devient donc automatiquement invalide
        # après activation. Sans cette vérification préalable, une réutilisation
        # du lien tomberait à tort dans le cas "lien invalide" au lieu de "déjà activé".
        if user.is_email_verified:
            return Response(
                {"detail": "Ce compte est déjà activé."},
                status=status.HTTP_200_OK
            )

        # check_token vérifie la signature ET que le token correspond à l'état actuel de l'utilisateur
        if account_activation_token.check_token(user, token):
            user.is_email_verified = True
            user.save()

            return Response(
                {"detail": "Compte activé avec succès."},
                status=status.HTTP_200_OK
            )

        return Response(
            {"detail": "Lien d'activation invalide ou expiré."},
            status=status.HTTP_400_BAD_REQUEST
        )


class PasswordResetRequestView(APIView):
    """
    Endpoint de demande de réinitialisation (POST /api/v1/accounts/password-reset/).
    Envoie un email contenant un lien de réinitialisation SI l'email existe.
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = password_reset_token.make_token(user)
            reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

            send_mail(
                subject="Réinitialisation de votre mot de passe",
                message=(
                    f"Bonjour {user.first_name or user.email},\n\n"
                    f"Vous avez demandé la réinitialisation de votre mot de passe.\n"
                    f"Cliquez sur ce lien pour en définir un nouveau :\n\n"
                    f"{reset_link}\n\n"
                    f"Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.\n\n"
                    f"L'équipe Crowdfunding Platform"
                ),
                from_email='noreply@crowdfunding.com',
                recipient_list=[user.email],
                fail_silently=False,
            )
        except User.DoesNotExist:
            # IMPORTANT : on ne fait RIEN de spécial ici, volontairement.
            # On ne doit jamais révéler si un email existe ou non dans le système.
            pass

        # Réponse IDENTIQUE que l'email existe ou non (sécurité)
        return Response(
            {"detail": "Si un compte existe avec cet email, un lien de réinitialisation a été envoyé."},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    """
    Endpoint de confirmation (POST /api/v1/accounts/password-reset/confirm/).
    Définit le nouveau mot de passe si le token est valide.
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        new_password = serializer.validated_data['new_password']

        # set_password hash automatiquement le mot de passe avant de le stocker
        user.set_password(new_password)
        user.save()

        return Response(
            {"detail": "Mot de passe réinitialisé avec succès."},
            status=status.HTTP_200_OK
        )
    