from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
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
    # Documentation API (OpenAPI / Swagger / Redoc)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# En développement uniquement : sert les fichiers uploadés (MEDIA_ROOT) via Django lui-même.
# En production, un vrai serveur web (nginx, etc.) ou un stockage cloud (S3) s'en charge.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)