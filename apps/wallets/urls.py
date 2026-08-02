from django.urls import path
from .views import MyWalletView, MyWalletHistoryView

app_name = 'wallets'

urlpatterns = [
    path('wallet/me/', MyWalletView.as_view(), name='my_wallet'),
    path('wallet/me/history/', MyWalletHistoryView.as_view(), name='my_wallet_history'),
]
