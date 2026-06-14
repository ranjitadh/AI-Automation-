from django.urls import path
from . import views

urlpatterns = [
    path('stats/', views.AdminStatsView.as_view(), name='admin-stats'),
    path('users/', views.AdminUsersView.as_view(), name='admin-users'),
    path('orgs/', views.AdminOrgsView.as_view(), name='admin-orgs'),
    path('plans/', views.AdminPlansView.as_view(), name='admin-plans'),
    path('audit-logs/', views.AdminAuditLogsView.as_view(), name='admin-audit-logs'),
]
