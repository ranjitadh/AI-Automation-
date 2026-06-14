from rest_framework.permissions import BasePermission

class IsOrgMember(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        org = getattr(request, 'org', None)
        if org is None:
            return False
        membership = getattr(request, 'membership', None)
        if membership is None:
            membership = request.user.memberships.filter(organization=org).first()
            request.membership = membership
        return membership is not None

class IsOrgAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        org = getattr(request, 'org', None)
        if org is None:
            return False
        membership = getattr(request, 'membership', None)
        if membership is None:
            membership = request.user.memberships.filter(organization=org).first()
            request.membership = membership
        return membership and membership.role in ('owner', 'admin')

class IsOrgOwner(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        org = getattr(request, 'org', None)
        if org is None:
            return False
        membership = getattr(request, 'membership', None)
        if membership is None:
            membership = request.user.memberships.filter(organization=org).first()
            request.membership = membership
        return membership and membership.role == 'owner'

class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)

class HasRole(BasePermission):
    def __init__(self, *roles):
        self.roles = roles

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        org = getattr(request, 'org', None)
        if org is None:
            return False
        membership = getattr(request, 'membership', None)
        if membership is None:
            membership = request.user.memberships.filter(organization=org).first()
            request.membership = membership
        return membership and membership.role in self.roles
