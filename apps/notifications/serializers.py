from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'notification_type', 'title', 'message', 'is_read', 'created_at')
        read_only_fields = ('id', 'notification_type', 'title', 'message', 'created_at')
        # is_read n'est PAS dans read_only_fields -- c'est le SEUL champ qu'un
        # utilisateur peut modifier lui-meme (marquer comme lu), via PATCH.
