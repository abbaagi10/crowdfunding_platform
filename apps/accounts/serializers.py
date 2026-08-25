from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'inscription d'un nouvel utilisateur.
    Gère la validation du mot de passe et la confirmation.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True, label="Confirmation du mot de passe")

    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'first_name', 'last_name', 'role')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Les deux mots de passe ne correspondent pas."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=validated_data.get('role', User.Role.INVESTISSEUR),
        )
        return user

    def validate_role(self, value):
        allowed_public_roles = (User.Role.INVESTISSEUR, User.Role.ENTREPRISE)
        if value not in allowed_public_roles:
            raise serializers.ValidationError(
                "Ce rôle n'est pas disponible pour l'inscription publique."
            )
        return value


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer utilisé pour AFFICHER les informations d'un utilisateur.
    ✅ Inclut is_active pour l'administration.
    """

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'role', 'is_email_verified', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Surcharge du serializer de connexion JWT standard.
    Ajoute une vérification supplémentaire : le compte doit être activé (email vérifié)
    avant de pouvoir se connecter.
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.is_email_verified:
            raise AuthenticationFailed(
                "Veuillez activer votre compte via le lien envoyé par email avant de vous connecter.",
                code="email_not_verified"
            )

        return data


password_reset_token = PasswordResetTokenGenerator()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Les deux mots de passe ne correspondent pas."})

        try:
            uid = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"uid": "Lien de réinitialisation invalide."})

        if not password_reset_token.check_token(user, attrs['token']):
            raise serializers.ValidationError({"token": "Lien de réinitialisation invalide ou expiré."})

        attrs['user'] = user
        return attrs