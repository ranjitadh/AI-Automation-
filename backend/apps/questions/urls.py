from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'bank', views.QuestionBankViewSet, basename='question-bank')
router.register(r'answers', views.QuestionAnswerViewSet, basename='question-answers')

urlpatterns = [
    path('', include(router.urls)),
]
