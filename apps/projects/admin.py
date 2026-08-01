from django.contrib import admin
from .models import Category, Project


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    Interface d'administration des projets.
    Permet à l'équipe UserAdmin/SuperAdmin de consulter et modérer les projets.
    """

    list_display = (
        'title', 'company', 'category', 'status',
        'funding_goal', 'current_amount', 'funding_percentage_display', 'created_at'
    )
    list_filter = ('status', 'category')
    search_fields = ('title', 'company__company_name')
    readonly_fields = ('slug', 'current_amount', 'created_at', 'updated_at')

    fieldsets = (
        ('Porteur de projet', {'fields': ('company', 'category')}),
        ('Contenu', {
            'fields': ('title', 'slug', 'short_description', 'full_description', 'cover_image')
        }),
        ('Financement', {
            'fields': ('funding_goal', 'current_amount')
        }),
        ('Calendrier', {
            'fields': ('start_date', 'end_date')
        }),
        ('Validation', {
            'fields': ('status', 'admin_feedback')
        }),
        ('Horodatage', {'fields': ('created_at', 'updated_at')}),
    )

    def funding_percentage_display(self, obj):
        return f"{obj.funding_percentage}%"
    funding_percentage_display.short_description = "% Financé"
