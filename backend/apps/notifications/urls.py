from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.NotificationViewSet, basename='notifications')
router.register(r'webhooks', views.WebhookViewSet, basename='webhooks')

urlpatterns = [
    path('', include(router.urls)),
]
