from django.urls import path
from .views import (
    MyWalletView,
    MyWalletHistoryView,
    WalletListView,
    WalletDetailView,
    WalletHistoryDetailView,
)

app_name = 'wallets'

urlpatterns = [
    path('wallet/me/', MyWalletView.as_view(), name='my_wallet'),
    path('wallet/me/history/', MyWalletHistoryView.as_view(), name='my_wallet_history'),

    # Endpoints d'audit, reserves a l'administration
    path('wallets/', WalletListView.as_view(), name='wallet_list'),
    path('wallets/<int:pk>/', WalletDetailView.as_view(), name='wallet_detail'),
    path('wallets/<int:pk>/history/', WalletHistoryDetailView.as_view(), name='wallet_history_detail'),
]
