from django.conf import settings
from django.utils import timezone


class OrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.org = None
        request.membership = None
        org_id = request.headers.get('X-Organization-ID') or request.session.get('organization_id')
        if org_id:
            try:
                from apps.accounts.models import Organization
                request.org = Organization.objects.get(id=org_id)
            except (Organization.DoesNotExist, ValueError, TypeError):
                pass
        return self.get_response(request)


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        script_src = "'self' 'unsafe-inline' https://js.stripe.com"
        if settings.DEBUG:
            script_src += " 'unsafe-eval'"
        response['Content-Security-Policy'] = (
            f"default-src 'self'; "
            f"script-src {script_src}; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' data:; "
            "frame-src https://js.stripe.com; "
            "connect-src 'self' http://127.0.0.1:3000 http://localhost:3000 https://api.stripe.com ws://127.0.0.1:3000 ws://localhost:3000; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        return response
