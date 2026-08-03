from django.urls import path
from .views import (
    GeneratePlanView,
    PayInstallmentView,
    MyRepaymentListView,
    ProjectRepaymentPlanView,
)

app_name = 'repayments'

urlpatterns = [
    path('plans/generate/<int:project_id>/', GeneratePlanView.as_view(), name='generate_plan'),
    path('plans/project/<int:project_id>/', ProjectRepaymentPlanView.as_view(), name='project_plan'),
    path('me/', MyRepaymentListView.as_view(), name='my_repayments'),
    path('<int:pk>/pay/', PayInstallmentView.as_view(), name='pay_installment'),
]
