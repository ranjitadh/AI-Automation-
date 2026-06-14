from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sessions', views.BrowserSessionViewSet, basename='browser-sessions')
router.register(r'runs', views.AutomationRunViewSet, basename='automation-runs')
router.register(r'logs', views.AutomationLogViewSet, basename='automation-logs')

urlpatterns = [
    path('', include(router.urls)),
]
