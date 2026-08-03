from django.urls import path
from .views import MyNotificationListView, MarkNotificationReadView, UnreadNotificationCountView

app_name = 'notifications'

urlpatterns = [
    path('me/', MyNotificationListView.as_view(), name='my_notifications'),
    path('unread-count/', UnreadNotificationCountView.as_view(), name='unread_count'),
    path('<int:pk>/read/', MarkNotificationReadView.as_view(), name='mark_read'),
]
