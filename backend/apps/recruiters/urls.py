from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.RecruiterViewSet, basename='recruiters')
router.register(r'outreach', views.RecruiterOutreachViewSet, basename='recruiter-outreach')

urlpatterns = [
    path('', include(router.urls)),
]
