from django.contrib import admin
from .models import InvestorProfile


@admin.register(InvestorProfile)
class InvestorProfileAdmin(admin.ModelAdmin):
    """
    Interface d'administration du profil investisseur.
    Permet à l'équipe UserAdmin/SuperAdmin de consulter et valider les dossiers KYC.
    """

    list_display = (
        'user', 'nationality', 'phone_number',
        'verification_status', 'is_kyc_complete_display', 'created_at'
    )
    list_filter = ('verification_status', 'nationality', 'country')
    search_fields = ('user__email', 'phone_number', 'nationality')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Utilisateur', {'fields': ('user',)}),
        ('Informations personnelles', {
            'fields': ('date_of_birth', 'nationality', 'phone_number')
        }),
        ('Adresse', {
            'fields': ('address_line', 'city', 'postal_code', 'country')
        }),
        ('Documents KYC', {
            'fields': ('profile_photo', 'identity_document', 'proof_of_address')
        }),
        ('Vérification', {
            'fields': ('verification_status', 'rejection_reason')
        }),
        ('Horodatage', {'fields': ('created_at', 'updated_at')}),
    )

    def is_kyc_complete_display(self, obj):
        """
        Affiche la propriété calculée is_kyc_complete dans la liste admin.
        Les méthodes personnalisées dans list_display doivent retourner
        une valeur affichable (ici un booléen, Django l'affiche avec une icône ✓/✗).
        """
        return obj.is_kyc_complete
    is_kyc_complete_display.short_description = "KYC complet"
    is_kyc_complete_display.boolean = True  # Affiche une icône plutôt que True/False en texte