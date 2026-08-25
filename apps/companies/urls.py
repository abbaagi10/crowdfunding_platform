from django.urls import path
from .views import (
    MyCompanyProfileView,
    CompanyProfileListView,
    CompanyProfileDetailView,
    CompanyProfileVerificationView,
    UploadCompanyLogoView,
    UploadRegistrationDocumentView,
    UploadIdentityDocumentView,
)

urlpatterns = [
    # Profil de l'utilisateur connecté
    path('profile/me/', MyCompanyProfileView.as_view(), name='company-profile-me'),
    
    # Liste et détail des profils (admin)
    path('profiles/', CompanyProfileListView.as_view(), name='company-profile-list'),
    path('profiles/<int:pk>/', CompanyProfileDetailView.as_view(), name='company-profile-detail'),
    path('profiles/<int:pk>/verify/', CompanyProfileVerificationView.as_view(), name='company-profile-verify'),
    
    # Upload de fichiers
    path('profile/upload-logo/', UploadCompanyLogoView.as_view(), name='upload-logo'),
    path('profile/upload-registration/', UploadRegistrationDocumentView.as_view(), name='upload-registration'),
    path('profile/upload-identity/', UploadIdentityDocumentView.as_view(), name='upload-identity'),
]