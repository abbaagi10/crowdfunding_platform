from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class MyNotificationListView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/notifications/me/
    Toutes les notifications de l'utilisateur connecte, plus recentes en premier.
    """
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MarkNotificationReadView(APIView):
    """
    Endpoint PATCH /api/v1/notifications/<id>/read/
    Marque UNE notification precise comme lue -- uniquement la SIENNE.
    """
    permission_classes = (IsAuthenticated,)

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({"detail": "Notification introuvable."}, status=status.HTTP_404_NOT_FOUND)

        notification.is_read = True
        notification.save()
        return Response(NotificationSerializer(notification).data)


class UnreadNotificationCountView(APIView):
    """
    Endpoint GET /api/v1/notifications/unread-count/
    Utile pour afficher un badge "3" sur une icone de cloche, sans
    devoir recuperer TOUTES les notifications juste pour les compter.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"unread_count": count})
