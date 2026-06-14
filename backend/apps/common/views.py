import logging
from django.db import connections
from django.conf import settings
from django.http import JsonResponse
from rest_framework import viewsets, mixins, generics, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import FileUpload, OrganizationSettings, Skill
from .serializers import FileUploadSerializer, OrganizationSettingsSerializer, SkillSerializer
from .permissions import IsOrgMember, IsOrgAdmin
from .mixins import OrganizationFilterMixin
from .pagination import StandardPagination

logger = logging.getLogger(__name__)


def health_check(request):
    import redis
    from django_redis import get_redis_connection
    status_code = 200
    checks = {
        'status': 'ok',
        'database': 'unknown',
        'redis': 'unknown',
        'version': '1.0.0',
    }
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {e}'
        status_code = 503

    try:
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        r.ping()
        checks['redis'] = 'ok'
        r.close()
    except Exception as e:
        checks['redis'] = f'error: {e}'
        status_code = 503

    return JsonResponse(checks, status=status_code)


class FileUploadViewSet(OrganizationFilterMixin,
                         mixins.CreateModelMixin,
                         mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    queryset = FileUpload.objects.all()
    serializer_class = FileUploadSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    pagination_class = StandardPagination
    search_fields = ['filename']
    ordering_fields = ['created_at', 'filename']

    def get_queryset(self):
        return super().get_queryset()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.org, user=self.request.user)


class OrganizationSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = OrganizationSettingsSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get_object(self):
        return OrganizationSettings.objects.get_or_create(organization_id=self.request.org.id)[0]


class SkillListView(generics.ListAPIView):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination
    search_fields = ['name', 'category']
    ordering_fields = ['name', 'category']
