from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed

# get_user_model() retourne le CustomUser configuré dans AUTH_USER_MODEL
# C'est la manière RECOMMANDÉE d'accéder au modèle User dans du code réutilisable
# (plutôt que d'importer CustomUser directement, ce qui casserait si on changeait encore de modèle)
User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'inscription d'un nouvel utilisateur.
    Gère la validation du mot de passe et la confirmation.
    """

    # write_only=True : ce champ est accepté en entrée (POST) mais jamais renvoyé en sortie (sécurité)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]  # Applique les AUTH_PASSWORD_VALIDATORS de Django
    )
    password2 = serializers.CharField(write_only=True, required=True, label="Confirmation du mot de passe")

    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'first_name', 'last_name', 'role')

    def validate(self, attrs):
        """
        Validation au niveau de l'objet entier (pas d'un seul champ).
        Ici on vérifie que les deux mots de passe saisis correspondent.
        """
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Les deux mots de passe ne correspondent pas."})
        return attrs

    def create(self, validated_data):
        """
        Surcharge de la création : on utilise notre manager personnalisé
        pour garantir que le mot de passe est bien hashé (jamais stocké en clair).
        """
        # On retire password2, il ne fait pas partie du modèle CustomUser
        validated_data.pop('password2')

        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=validated_data.get('role', User.Role.INVESTISSEUR),
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer utilisé pour AFFICHER les informations d'un utilisateur.
    Ne contient jamais le mot de passe (jamais dans 'fields').
    """

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'role', 'is_email_verified', 'created_at')
        read_only_fields = ('id', 'created_at')


from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Surcharge du serializer de connexion JWT standard.
    Ajoute une vérification supplémentaire : le compte doit être activé (email vérifié)
    avant de pouvoir se connecter.
    """

    def validate(self, attrs):
        # La méthode parente vérifie déjà email + mot de passe,
        # et lève une erreur 401 automatiquement si invalides
        data = super().validate(attrs)

        # self.user est défini par la classe parente après validation réussie des identifiants
        if not self.user.is_email_verified:
            raise AuthenticationFailed(
                "Veuillez activer votre compte via le lien envoyé par email avant de vous connecter.",
                code="email_not_verified"
            )

        return data        