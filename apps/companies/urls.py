from django.urls import path
from .views import (
    MyCompanyProfileView,
    CompanyProfileListView,
    CompanyProfileDetailView,
    CompanyProfileVerificationView,
)

app_name = 'companies'

urlpatterns = [
    path('profile/me/', MyCompanyProfileView.as_view(), name='my_profile'),
    path('profiles/', CompanyProfileListView.as_view(), name='profile_list'),
    path('profiles/<int:pk>/', CompanyProfileDetailView.as_view(), name='profile_detail'),
    path('profiles/<int:pk>/verify/', CompanyProfileVerificationView.as_view(), name='profile_verify'),
]
