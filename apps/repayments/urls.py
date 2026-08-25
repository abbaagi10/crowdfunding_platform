from django.urls import path
from .views import (
    MyRepaymentsView,
    ProjectRepaymentPlanView,
    GenerateRepaymentPlanView,
    PayRepaymentView,
    CancelInvestmentView,
)

app_name = 'repayments'

urlpatterns = [
    path('me/', MyRepaymentsView.as_view(), name='my-repayments'),
    path('plans/project/<int:project_id>/', ProjectRepaymentPlanView.as_view(), name='project-plan'),
    path('plans/generate/<int:project_id>/', GenerateRepaymentPlanView.as_view(), name='generate-plan'),
    path('<int:id>/pay/', PayRepaymentView.as_view(), name='pay-repayment'),
    path('cancel/<int:id>/', CancelInvestmentView.as_view(), name='cancel-investment'),
]