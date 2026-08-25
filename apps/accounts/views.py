from django.contrib.auth import get_user_model
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.core.mail import send_mail
from django.conf import settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
import requests

from .serializers import (
    RegisterSerializer, 
    UserSerializer, 
    CustomTokenObtainPairSerializer
)
from .tokens import account_activation_token
from .serializers import (
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    password_reset_token,
)
from .permissions import IsAdminOrSuperAdmin

User = get_user_model()


class GoogleLoginView(APIView):
    """
    Connexion avec Google via OAuth2
    POST /api/v1/auth/google/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        access_token = request.data.get('access_token')
        
        if not access_token:
            return Response(
                {'error': 'Access token requis.'},
                status=400
            )
        
        try:
            # Vérifier le token avec Google
            response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if response.status_code != 200:
                return Response(
                    {'error': 'Token Google invalide.'},
                    status=400
                )
            
            user_data = response.json()
            email = user_data.get('email')
            
            if not email:
                return Response(
                    {'error': 'Email non trouvé.'},
                    status=400
                )
            
            # ✅ Vérifier si l'utilisateur existe
            try:
                user = User.objects.get(email=email)
                # Utilisateur existe → connexion directe
                refresh = RefreshToken.for_user(user)
                return Response({
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': UserSerializer(user).data,
                    'is_new': False,
                })
            except User.DoesNotExist:
                # ✅ Nouvel utilisateur → créer avec rôle par défaut
                print(f"🆕 [GOOGLE] Nouvel utilisateur: {email}")
                
                user = User.objects.create_user(
                    email=email,
                    password=None,  # Pas de mot de passe pour Google
                    first_name=user_data.get('given_name', ''),
                    last_name=user_data.get('family_name', ''),
                    role='INVESTISSEUR',  # Rôle par défaut
                    is_email_verified=True,
                    is_active=True,
                )
                
                # Créer les tokens JWT
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': UserSerializer(user).data,
                    'is_new': True,
                    'needs_role': True,  # Indique qu'on doit demander le rôle
                })
            
        except Exception as e:
            print(f"❌ Erreur Google login: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': 'Erreur lors de la connexion Google.'},
                status=500
            )


class UpdateUserRoleView(APIView):
    """
    Mettre à jour le rôle de l'utilisateur
    POST /api/v1/accounts/update-role/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        role = request.data.get('role')
        
        if role not in ['INVESTISSEUR', 'ENTREPRISE']:
            return Response(
                {'error': 'Rôle invalide. Choisissez INVESTISSEUR ou ENTREPRISE.'},
                status=400
            )
        
        user = request.user
        
        # Vérifier si l'utilisateur peut changer de rôle
        # (uniquement si le rôle actuel est INVESTISSEUR par défaut)
        if user.role != 'INVESTISSEUR' or user.pk != request.user.pk:
            return Response(
                {'error': 'Vous ne pouvez pas modifier ce rôle.'},
                status=403
            )
        
        user.role = role
        user.save()
        
        return Response({
            'message': f'Rôle mis à jour avec succès vers {role}',
            'user': UserSerializer(user).data
        })


# ============================================
# Autres vues (RegisterView, LoginView, etc.)
# ============================================

class RegisterView(generics.CreateAPIView):
    """
    Endpoint d'inscription (POST /api/v1/accounts/register/).
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            "user": UserSerializer(user).data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(BaseTokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(
    tags=['accounts'],
    request={'application/json': {'type': 'object', 'properties': {'refresh': {'type': 'string'}}}},
    responses={205: OpenApiResponse(description="Déconnexion réussie.")}
)
class LogoutView(APIView):
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


@extend_schema(
    tags=['accounts'],
    responses={200: UserSerializer}
)
class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


@extend_schema(
    tags=['accounts'],
    responses={200: OpenApiResponse(description="Compte activé avec succès.")}
)
class ActivateAccountView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Lien d'activation invalide ou expiré."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_email_verified:
            return Response(
                {"detail": "Ce compte est déjà activé."},
                status=status.HTTP_200_OK
            )

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


@extend_schema(
    tags=['accounts'],
    request=PasswordResetRequestSerializer,
    responses={200: OpenApiResponse(description="Email de réinitialisation envoyé si le compte existe.")}
)
class PasswordResetRequestView(APIView):
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
            pass

        return Response(
            {"detail": "Si un compte existe avec cet email, un lien de réinitialisation a été envoyé."},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=['accounts'],
    request=PasswordResetConfirmSerializer,
    responses={200: OpenApiResponse(description="Mot de passe réinitialisé avec succès.")}
)
class PasswordResetConfirmView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        new_password = serializer.validated_data['new_password']

        user.set_password(new_password)
        user.save()

        return Response(
            {"detail": "Mot de passe réinitialisé avec succès."},
            status=status.HTTP_200_OK
        )


class UserListView(generics.ListAPIView):
    queryset = User.objects.all().order_by('-created_at')
    serializer_class = UserSerializer
    permission_classes = (IsAdminOrSuperAdmin,)


class ResendActivationEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Si un compte existe avec cet email, un nouveau lien d\'activation a été envoyé.'},
                status=status.HTTP_200_OK
            )
        
        if user.is_email_verified:
            return Response(
                {'error': 'Ce compte est déjà activé.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        activate_url = f"{settings.FRONTEND_URL}/activate/{uid}/{token}/"
        
        send_mail(
            subject="Activez votre compte Arzeeki",
            message=f"""
            Bonjour {user.first_name or 'Utilisateur'},
            
            Vous avez demandé un nouveau lien d'activation pour votre compte Arzeeki.
            
            Cliquez sur le lien ci-dessous pour activer votre compte :
            {activate_url}
            
            Ce lien est valable 24h.
            
            Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.
            
            -- 
            L'équipe Arzeeki
            Zancen kasa né · Laabu sanni nô · Pour la patrie
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        return Response({
            'detail': 'Un nouveau lien d\'activation a été envoyé à votre adresse email.'
        })