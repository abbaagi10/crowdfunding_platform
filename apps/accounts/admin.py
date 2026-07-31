from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Personnalisation de l'affichage de CustomUser dans l'admin Django.
    On hérite de UserAdmin pour garder tout le comportement natif
    (gestion des mots de passe hashés, groupes, permissions...).
    """

    # Champs affichés dans la liste des utilisateurs
    list_display = ('email', 'role', 'is_active', 'is_email_verified', 'is_staff', 'created_at')

    # Filtres disponibles dans la barre latérale
    list_filter = ('role', 'is_active', 'is_email_verified', 'is_staff')

    # Champ de recherche
    search_fields = ('email',)

    # Tri par défaut
    ordering = ('-created_at',)

    # Organisation des champs dans le formulaire de modification
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name')}),
        ('Rôle et statut', {'fields': ('role', 'is_email_verified')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates importantes', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    # Organisation des champs dans le formulaire de CRÉATION d'utilisateur
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role'),
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'last_login')