from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

router = DefaultRouter()
router.register(r'orgs', views.OrganizationViewSet, basename='orgs')

urlpatterns = [
    path('login/', views.AuthView.as_view(), name='auth-login'),
    path('register/', views.RegisterView.as_view(), name='auth-register'),
    path('me/', views.MeView.as_view(), name='auth-me'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('', include(router.urls)),
]
