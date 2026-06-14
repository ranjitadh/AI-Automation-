from rest_framework import viewsets, serializers, status, generics, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, Organization, Team, Membership
import uuid
from apps.common.permissions import IsOrgAdmin, IsOrgOwner
from apps.common.mixins import OrganizationFilterMixin

class AuthRateThrottle(UserRateThrottle):
    rate = '10/min'

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8)
    full_name = serializers.CharField()
    organization_name = serializers.CharField()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'avatar_url', 'timezone', 'locale', 'date_joined')
        read_only_fields = ('id', 'date_joined')

class OrganizationSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ('id', 'name', 'slug', 'logo_url', 'website', 'is_active', 'created_at', 'updated_at', 'role', 'member_count')
        read_only_fields = ('id', 'created_at', 'updated_at', 'slug')

    def get_role(self, obj):
        user = self.context.get('user') or self.context['request'].user
        if user.is_anonymous:
            return None
        membership = user.memberships.only('role').filter(organization=obj).first()
        return membership.role if membership else None

    def get_member_count(self, obj):
        return obj.memberships.count()

class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Membership
        fields = ('id', 'user', 'user_email', 'user_name', 'organization', 'team', 'role', 'is_default', 'invited_by', 'invited_at', 'accepted_at', 'joined_at')
        read_only_fields = ('id', 'organization', 'invited_by', 'invited_at', 'accepted_at', 'joined_at')

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ('id', 'organization', 'name', 'description', 'created_at')
        read_only_fields = ('id', 'organization', 'created_at')

class AuthView(views.APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = authenticate(email=s.validated_data['email'], password=s.validated_data['password'])
        if not user:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(user)
        organizations = Organization.objects.filter(memberships__user=user)
        orgs = OrganizationSerializer(organizations, many=True, context={'request': request}).data
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'organizations': orgs,
        })

class RegisterView(views.APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if User.objects.filter(email=s.validated_data['email']).exists():
            return Response({'error': 'Email already registered'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(
            email=s.validated_data['email'],
            password=s.validated_data['password'],
            full_name=s.validated_data['full_name'],
        )
        org = Organization.objects.create(
            name=s.validated_data['organization_name'],
            slug=s.validated_data['organization_name'].lower().replace(' ', '-'),
        )
        Membership.objects.create(user=user, organization=org, role='owner', is_default=True)
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'organization': OrganizationSerializer(org, context={'request': request, 'user': user}).data,
        }, status=status.HTTP_201_CREATED)

class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        return Organization.objects.filter(memberships__user=self.request.user).prefetch_related('memberships')

    def perform_create(self, serializer):
        org = serializer.save()
        Membership.objects.create(user=self.request.user, organization=org, role='owner', is_default=True)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        org = self.get_object()
        memberships = Membership.objects.filter(organization=org).select_related('user')
        return Response(MembershipSerializer(memberships, many=True).data)

    @action(detail=True, methods=['post'])
    def invite(self, request, pk=None):
        org = self.get_object()
        requesting_membership = request.user.memberships.filter(organization=org).first()
        if not requesting_membership or requesting_membership.role not in ('owner', 'admin'):
            return Response({'error': 'Only admins can invite members'}, status=403)
        email = request.data.get('email')
        role = request.data.get('role', 'member')
        if not email:
            return Response({'error': 'Email required'}, status=400)
        if role not in ('admin', 'member', 'viewer'):
            return Response({'error': 'Invalid role'}, status=400)
        user = User.objects.filter(email=email).first()
        if not user:
            user = User.objects.create_user(email=email, password=uuid.uuid4().hex[:12])
        Membership.objects.get_or_create(user=user, organization=org, defaults={'role': role, 'invited_by': request.user})
        return Response({'status': 'invited'})

    @action(detail=True, methods=['patch', 'delete'], url_path='members/(?P<member_id>[^/.]+)')
    def member_update(self, request, pk=None, member_id=None):
        org = self.get_object()
        requesting_membership = request.user.memberships.filter(organization=org).first()
        if not requesting_membership or requesting_membership.role not in ('owner', 'admin'):
            return Response({'error': 'Only admins can manage members'}, status=403)
        membership = Membership.objects.get(organization=org, id=member_id)
        if request.method == 'DELETE':
            if membership.role == 'owner':
                return Response({'error': 'Cannot remove the owner'}, status=400)
            membership.delete()
            return Response(status=204)
        membership.role = request.data.get('role', membership.role)
        if membership.role not in ('admin', 'member', 'viewer'):
            return Response({'error': 'Invalid role'}, status=400)
        membership.save()
        return Response(MembershipSerializer(membership).data)

    @action(detail=True)
    def teams(self, request, pk=None):
        org = self.get_object()
        teams = Team.objects.filter(organization=org)
        return Response(TeamSerializer(teams, many=True).data)

    @action(detail=True, methods=['post'])
    def switch(self, request, pk=None):
        try:
            org = Organization.objects.get(id=pk)
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=404)
        membership = request.user.memberships.filter(organization=org).first()
        if not membership:
            return Response({'error': 'Not a member'}, status=403)
        request.user.current_organization = org
        request.user.save(update_fields=['current_organization'])
        request.session['organization_id'] = str(org.id)
        return Response({'status': 'switched', 'organization': OrganizationSerializer(org, context={'request': request}).data})
