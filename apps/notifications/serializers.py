from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    Sérialiseur pour les notifications.
    """
    recipient_email = serializers.EmailField(source='recipient.email', read_only=True)
    
    class Meta:
        model = Notification
        fields = (
            'id', 'recipient', 'recipient_email',
            'notification_type', 'title', 'message', 'data',
            'is_read', 'read_at', 'created_at'
        )
        read_only_fields = ('id', 'recipient', 'recipient_email', 'created_at', 'read_at')


class UnreadCountSerializer(serializers.Serializer):
    """
    Sérialiseur pour le nombre de notifications non lues.
    """
    unread_count = serializers.IntegerField()