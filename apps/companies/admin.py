from django.contrib import admin
from .models import CompanyProfile


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    """
    Interface d'administration du profil entreprise.
    Permet à l'équipe UserAdmin/SuperAdmin de consulter et valider les dossiers KYB.
    """

    list_display = (
        'company_name', 'registration_number', 'user',
        'verification_status', 'is_kyb_complete_display', 'created_at'
    )
    list_filter = ('verification_status', 'company_type', 'country')
    search_fields = ('company_name', 'registration_number', 'user__email')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Utilisateur', {'fields': ('user',)}),
        ('Informations légales', {
            'fields': ('company_name', 'registration_number', 'company_type', 'industry_sector', 'website')
        }),
        ('Représentant légal', {
            'fields': ('legal_representative_name', 'legal_representative_position', 'legal_representative_phone')
        }),
        ('Adresse du siège social', {
            'fields': ('address_line', 'city', 'postal_code', 'country')
        }),
        ('Informations bancaires', {
            'fields': ('iban', 'bic_swift', 'bank_name')
        }),
        ('Documents KYB', {
            'fields': ('company_logo', 'registration_document', 'legal_representative_id_document')
        }),
        ('Vérification', {
            'fields': ('verification_status', 'rejection_reason')
        }),
        ('Horodatage', {'fields': ('created_at', 'updated_at')}),
    )

    def is_kyb_complete_display(self, obj):
        return obj.is_kyb_complete
    is_kyb_complete_display.short_description = "KYB complet"
    is_kyb_complete_display.boolean = True
