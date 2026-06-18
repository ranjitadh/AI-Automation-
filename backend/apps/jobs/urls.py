from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.JobViewSet, basename='jobs')
router.register(r'companies', views.CompanyViewSet, basename='companies')
router.register(r'sources', views.JobSourceViewSet, basename='job-sources')

urlpatterns = [
    path('', include(router.urls)),
]
