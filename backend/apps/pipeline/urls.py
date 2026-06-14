from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PipelineRunViewSet

router = DefaultRouter()
router.register(r'', PipelineRunViewSet, basename='pipelinerun')

urlpatterns = [
    path('', include(router.urls)),
]
