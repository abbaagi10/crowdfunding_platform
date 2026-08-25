from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer, UnreadCountSerializer


class NotificationListView(generics.ListAPIView):
    """
    Liste des notifications de l'utilisateur connecté.
    GET /api/v1/notifications/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class UnreadCountView(APIView):
    """
    Nombre de notifications non lues.
    GET /api/v1/notifications/unread-count/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        serializer = UnreadCountSerializer({'unread_count': count})
        return Response(serializer.data)


class MarkAsReadView(APIView):
    """
    Marquer une notification comme lue.
    PATCH /api/v1/notifications/{id}/read/
    """
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, recipient=request.user)
            notification.mark_as_read()
            serializer = NotificationSerializer(notification)
            return Response(serializer.data)
        except Notification.DoesNotExist:
            return Response(
                {'detail': 'Notification non trouvée.'},
                status=status.HTTP_404_NOT_FOUND
            )


class MarkAllAsReadView(APIView):
    """
    Marquer toutes les notifications comme lues.
    PATCH /api/v1/notifications/read-all/
    """
    permission_classes = [IsAuthenticated]
    
    def patch(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        return Response({
            'detail': f'{count} notification(s) marquée(s) comme lue(s).'
        })