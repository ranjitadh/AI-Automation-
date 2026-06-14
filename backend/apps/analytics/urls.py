from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='analytics-dashboard'),
    path('applications/', views.ApplicationAnalyticsView.as_view(), name='analytics-applications'),
    path('funnel/', views.FunnelView.as_view(), name='analytics-funnel'),
    path('trends/', views.TrendView.as_view(), name='analytics-trends'),
]
