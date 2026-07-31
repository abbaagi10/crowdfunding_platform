from django.contrib.auth.base_user import BaseUserManager


class CustomUserManager(BaseUserManager):
    """
    Manager personnalisé pour le modèle CustomUser.
    Remplace le manager par défaut de Django car nous utilisons
    l'email comme identifiant unique, au lieu du username.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Crée et sauvegarde un utilisateur standard avec l'email et le mot de passe donnés.
        """
        if not email:
            # On refuse la création si aucun email n'est fourni : c'est notre identifiant unique
            raise ValueError("L'adresse email est obligatoire.")

        # normalize_email met en minuscule la partie domaine (ex: @GMAIL.com -> @gmail.com)
        email = self.normalize_email(email)

        # self.model fait référence au modèle CustomUser (défini plus bas)
        user = self.model(email=email, **extra_fields)

        # set_password hash le mot de passe avant de le stocker (jamais en clair !)
        user.set_password(password)

        # using=self._db garantit qu'on utilise la bonne base de données configurée (utile en multi-DB)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Crée et sauvegarde un superutilisateur (accès admin total).
        Appelé automatiquement par la commande `createsuperuser`.
        """
        # On force les droits nécessaires, même si l'appelant ne les a pas précisés
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        # Sécurité : un superuser DOIT avoir is_staff=True et is_superuser=True
        if extra_fields.get('is_staff') is not True:
            raise ValueError("Le superuser doit avoir is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Le superuser doit avoir is_superuser=True.")

        return self.create_user(email, password, **extra_fields)