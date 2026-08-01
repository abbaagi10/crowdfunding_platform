from django.contrib.auth import get_user_model
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from .tokens import account_activation_token
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .serializers import RegisterSerializer, UserSerializer
from .serializers import CustomTokenObtainPairSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
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


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class ActivateAccountView(APIView):
    """
    Active le compte d'un utilisateur à partir du lien reçu par email.
    """
    permission_classes = (AllowAny,)

    def get(self, request, uidb64, token):
        try:
            # Décode l'ID utilisateur depuis l'URL
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        # check_token vérifie la signature ET que le token n'a pas déjà été utilisé/expiré
        if user is not None and account_activation_token.check_token(user, token):
            if user.is_email_verified:
                return Response(
                    {"detail": "Ce compte est déjà activé."},
                    status=status.HTTP_200_OK
                )

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

class CustomTokenObtainPairView(BaseTokenObtainPairView):
    """
    Vue de connexion personnalisée, utilisant notre serializer
    qui vérifie l'activation du compte.
    """
    serializer_class = CustomTokenObtainPairSerializer
    