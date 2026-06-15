from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Count, Sum
from django.contrib.auth import get_user_model
from apps.accounts.models import Organization
from apps.billing.models import Plan, Subscription
from apps.audit.models import AuditLog

User = get_user_model()

class AdminStatsView(generics.GenericAPIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response({
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'total_orgs': Organization.objects.count(),
            'active_orgs': Organization.objects.filter(is_active=True).count(),
            'total_subscriptions': Subscription.objects.count(),
            'active_subscriptions': Subscription.objects.filter(status='active').count(),
            'revenue': Subscription.objects.filter(status='active').aggregate(
                total=Sum('plan__price_monthly')
            )['total'] or 0,
        })

class AdminUsersView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    queryset = User.objects.all().order_by('-date_joined')
    search_fields = ['email', 'full_name']

    def get_serializer(self, *args, **kwargs):
        from apps.accounts.views import UserSerializer
        return UserSerializer(*args, **kwargs)

class AdminOrgsView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    queryset = Organization.objects.all().order_by('-created_at')
    search_fields = ['name', 'slug']

    def get_serializer(self, *args, **kwargs):
        from apps.accounts.views import OrganizationSerializer
        return OrganizationSerializer(*args, **kwargs)

class AdminPlansView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    queryset = Plan.objects.all().order_by('sort_order')

    def get_serializer(self, *args, **kwargs):
        from apps.billing.views import PlanSerializer
        return PlanSerializer(*args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()

class AdminAuditLogsView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    queryset = AuditLog.objects.all().order_by('-timestamp')[:100]
    search_fields = ['action', 'resource_type', 'resource_description']
