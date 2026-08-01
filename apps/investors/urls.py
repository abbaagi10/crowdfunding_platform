from django.urls import path
from .views import (
    MyInvestorProfileView,
    InvestorProfileListView,
    InvestorProfileDetailView,
    InvestorProfileVerificationView,
)

app_name = 'investors'

urlpatterns = [
    path('profile/me/', MyInvestorProfileView.as_view(), name='my_profile'),
    path('profiles/', InvestorProfileListView.as_view(), name='profile_list'),
    path('profiles/<int:pk>/', InvestorProfileDetailView.as_view(), name='profile_detail'),
    path('profiles/<int:pk>/verify/', InvestorProfileVerificationView.as_view(), name='profile_verify'),
]