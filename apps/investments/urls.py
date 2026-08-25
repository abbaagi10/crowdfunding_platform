from django.urls import path
from .views import (
    InvestmentListView,
    InvestmentMeView,
    InvestmentSummaryView,
    InvestmentProjectView,
)
from apps.repayments.views import CancelInvestmentView

app_name = 'investments'

urlpatterns = [
    path('', InvestmentListView.as_view(), name='investment-list'),
    path('me/', InvestmentMeView.as_view(), name='investment-me'),
    path('me/summary/', InvestmentSummaryView.as_view(), name='investment-summary'),
    path('project/<int:project_id>/', InvestmentProjectView.as_view(), name='investment-project'),
    path('<int:id>/cancel/', CancelInvestmentView.as_view(), name='cancel-investment'),
]