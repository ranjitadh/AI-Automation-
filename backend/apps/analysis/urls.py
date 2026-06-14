from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'job', views.JobAnalysisViewSet, basename='job-analysis')
router.register(r'ats', views.ATSAnalysisViewSet, basename='ats-analysis')

urlpatterns = [
    path('', include(router.urls)),
]
