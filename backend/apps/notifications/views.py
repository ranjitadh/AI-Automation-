from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification, Webhook
from apps.common.mixins import OrganizationFilterMixin
from apps.common.permissions import IsOrgMember, IsOrgAdmin
from django.utils import timezone
from django.db.models import Q

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'organization', 'user', 'type', 'channel', 'title', 'body', 'data', 'is_read', 'read_at', 'created_at', 'updated_at')
        read_only_fields = ('organization', 'read_at')

class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = ('id', 'organization', 'name', 'url', 'events', 'secret', 'is_active', 'last_triggered_at', 'last_success_at', 'last_failure_at', 'failure_count', 'created_at', 'updated_at')
        read_only_fields = ('organization', 'last_triggered_at', 'last_success_at', 'last_failure_at', 'failure_count')

class NotificationViewSet(OrganizationFilterMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    search_fields = ['title', 'body', 'type']
    ordering_fields = ['created_at', 'type']
    filterset_fields = ['type', 'channel', 'is_read']

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(Q(user=self.request.user) | Q(user__isnull=True))
        return qs.select_related('organization', 'user')

    @action(detail=True, methods=['patch'])
    def mark_read(self, request, pk=None):
        n = self.get_object()
        n.is_read = True
        n.read_at = timezone.now()
        n.save(update_fields=['is_read', 'read_at'])
        return Response({'status': 'read'})

    @action(detail=False, methods=['post'])
    def read_all(self, request):
        self.get_queryset().filter(user=request.user, is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({'status': 'all read'})

    @action(detail=False)
    def unread_count(self, request):
        count = self.get_queryset().filter(user=request.user, is_read=False).count()
        return Response({'count': count})

class WebhookViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    queryset = Webhook.objects.all()
    serializer_class = WebhookSerializer
    permission_classes = [IsAuthenticated, IsOrgAdmin]
    search_fields = ['name', 'url']
    ordering_fields = ['created_at']
    filterset_fields = ['is_active']

    def get_queryset(self):
        return super().get_queryset().select_related('organization')
