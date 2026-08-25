from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.admin.views import AdminStatsView
from apps.accounts.views import GoogleLoginView
from apps.investors.views import InvestorProfileListView
from apps.companies.views import CompanyProfileListView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include('apps.accounts.urls')),
    path('api/v1/investors/', include('apps.investors.urls')),
    path('api/v1/companies/', include('apps.companies.urls')),
    path('api/v1/projects/', include('apps.projects.urls')),
    path('api/v1/wallets/', include('apps.wallets.urls')),
    path('api/v1/transactions/', include('apps.transactions.urls')),
    path('api/v1/investments/', include('apps.investments.urls')),
    path('api/v1/repayments/', include('apps.repayments.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/admin/stats/', AdminStatsView.as_view(), name='admin-stats'),
    path('api/v1/investors/profiles/', InvestorProfileListView.as_view(), name='investor-profiles-list'),
    path('api/v1/companies/profiles/', CompanyProfileListView.as_view(), name='company-profiles-list'),
    
    # ✅ Google Login
    path('api/v1/auth/google/', GoogleLoginView.as_view(), name='google_login'),
    
    # Allauth
    path('api/v1/auth/', include('allauth.socialaccount.urls')),
    
    # Documentation API
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)