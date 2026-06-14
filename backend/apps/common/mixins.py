from django.db import models

class OrganizationFilterMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, 'org', None)
        if org is None:
            return qs.filter(pk=None)
        if hasattr(qs.model, 'organization'):
            return qs.filter(organization=org)
        return qs

    def perform_create(self, serializer):
        org = getattr(self.request, 'org', None)
        if org is None:
            return serializer.save()
        kwargs = {}
        if hasattr(serializer.Meta.model, 'organization'):
            kwargs['organization'] = org
        if hasattr(serializer.Meta.model, 'user') and 'user' not in serializer.validated_data:
            kwargs['user'] = self.request.user
        serializer.save(**kwargs)
