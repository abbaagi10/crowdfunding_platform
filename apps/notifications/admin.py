from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('recipient__email', 'title', 'message')
    readonly_fields = ('created_at', 'read_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Destinataire', {
            'fields': ('recipient',)
        }),
        ('Contenu', {
            'fields': ('notification_type', 'title', 'message', 'data')
        }),
        ('Statut', {
            'fields': ('is_read', 'read_at')
        }),
        ('Dates', {
            'fields': ('created_at',)
        }),
    )