from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OutreachEmailViewSet

router = DefaultRouter()
router.register(r'', OutreachEmailViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
