from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('user__email', 'title', 'message')
    readonly_fields = ('user', 'notification_type', 'title', 'message', 'created_at')

    def has_add_permission(self, request):
        # Les notifications sont creees UNIQUEMENT via create_notification.delay(),
        # jamais manuellement -- garantit la coherence avec l'evenement declencheur.
        return False
