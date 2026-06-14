from django.urls import path
from . import views

urlpatterns = [
    path('stripe/', views.StripeWebhookView.as_view(), name='stripe-webhook'),
]
