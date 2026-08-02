from django.urls import path
from .views import (
    MyInvestmentListView,
    MyInvestmentSummaryView,
    ProjectInvestmentListView,
    InvestmentListView,
)

app_name = 'investments'

urlpatterns = [
    path('me/', MyInvestmentListView.as_view(), name='my_investments'),
    path('me/summary/', MyInvestmentSummaryView.as_view(), name='my_investments_summary'),
    path('project/<int:project_id>/', ProjectInvestmentListView.as_view(), name='project_investments'),
    path('', InvestmentListView.as_view(), name='investment_list'),
]
