from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'plans', views.PlanViewSet, basename='plans')
router.register(r'invoices', views.InvoiceViewSet, basename='invoices')

urlpatterns = [
    path('subscription/', views.SubscriptionView.as_view(), name='subscription'),
    path('subscription/cancel/', views.SubscriptionCancelView.as_view(), name='subscription-cancel'),
    path('usage/', views.UsageView.as_view(), name='usage'),
    path('', include(router.urls)),
]

urlpatterns_webhooks = [
    path('stripe/', views.StripeWebhookView.as_view(), name='stripe-webhook'),
]
