from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'uploads', views.FileUploadViewSet, basename='fileupload')

urlpatterns = [
    path('', views.OrganizationSettingsView.as_view(), name='settings'),
    path('skills/', views.SkillListView.as_view(), name='skill-list'),
    path('', include(router.urls)),
]
