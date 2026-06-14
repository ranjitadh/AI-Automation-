import json
from django.utils import timezone
from apps.audit.models import AuditLog

class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and hasattr(request, 'org'):
            if hasattr(request, 'user') and request.user.is_authenticated:
                resource_type = request.path.split('/')[-2] if len(request.path.split('/')) > 2 else 'unknown'
                if response.status_code < 400:
                    AuditLog.objects.create(
                        organization=request.org,
                        user=request.user,
                        action=f"{request.method.lower()}_{resource_type}",
                        resource_type=resource_type,
                        metadata={
                            'path': request.path,
                            'method': request.method,
                            'status_code': response.status_code,
                            'ip': request.META.get('REMOTE_ADDR', ''),
                            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255],
                        }
                    )
        return response
