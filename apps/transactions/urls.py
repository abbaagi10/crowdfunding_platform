from django.urls import path
from .views import MyTransactionListView, DepositView, WithdrawView, InvestView, TransactionListView

app_name = 'transactions'

urlpatterns = [
    path('me/', MyTransactionListView.as_view(), name='my_transactions'),
    path('deposit/', DepositView.as_view(), name='deposit'),
    path('withdraw/', WithdrawView.as_view(), name='withdraw'),
    path('invest/', InvestView.as_view(), name='invest'),
    path('', TransactionListView.as_view(), name='transaction_list'),
]