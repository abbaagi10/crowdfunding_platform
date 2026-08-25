from django.urls import path
from .views import (
    NotificationListView,
    UnreadCountView,
    MarkAsReadView,
    MarkAllAsReadView,
)

app_name = 'notifications'

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('unread-count/', UnreadCountView.as_view(), name='unread-count'),
    path('<int:pk>/read/', MarkAsReadView.as_view(), name='mark-as-read'),
    path('read-all/', MarkAllAsReadView.as_view(), name='mark-all-as-read'),
]