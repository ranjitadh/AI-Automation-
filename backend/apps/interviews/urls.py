from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.InterviewViewSet, basename='interviews')

urlpatterns = [
    path('', include(router.urls)),
]

urlpatterns_offers = [
    path('', include(router.urls)),
]
