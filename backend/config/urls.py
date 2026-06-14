from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.common.views import health_check

api_patterns = [
    path('auth/', include('apps.accounts.urls')),
    path('resumes/', include('apps.resumes.urls')),
    path('jobs/', include('apps.jobs.urls')),
    path('analysis/', include('apps.analysis.urls')),
    path('campaigns/', include('apps.campaigns.urls')),
    path('applications/', include('apps.applications.urls')),
    path('cover-letters/', include('apps.cover_letters.urls')),
    path('questions/', include('apps.questions.urls')),
    path('interviews/', include('apps.interviews.urls')),
    path('offers/', include('apps.interviews.urls_offers')),
    path('recruiters/', include('apps.recruiters.urls')),
    path('automation/', include('apps.automation.urls')),
    path('billing/', include('apps.billing.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('analytics/', include('apps.analytics.urls')),
    path('settings/', include('apps.common.urls')),
    path('admin/', include('apps.admin_dashboard.urls')),
    path('webhooks/', include('apps.billing.urls_webhooks')),
    path('pipeline/', include('apps.pipeline.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(api_patterns)),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('health/', health_check, name='health_check'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
