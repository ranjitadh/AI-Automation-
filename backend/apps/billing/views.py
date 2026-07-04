from rest_framework import viewsets, serializers, status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum
from .models import Plan, Subscription, Invoice, UsageEvent
from apps.common.mixins import OrganizationFilterMixin
from apps.common.permissions import IsOrgMember, IsOrgOwner

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ('id', 'name', 'slug', 'description', 'price_monthly', 'price_yearly', 'max_applications_monthly', 'max_resumes', 'max_team_members', 'has_ats_optimization', 'has_auto_apply', 'has_analytics', 'has_api_access', 'has_priority_support', 'features', 'sort_order', 'is_active')
        read_only_fields = ('id',)

class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_slug = serializers.CharField(source='plan.slug', read_only=True)

    class Meta:
        model = Subscription
        fields = ('id', 'organization', 'plan', 'plan_name', 'plan_slug', 'status', 'billing_cycle', 'stripe_customer_id', 'stripe_subscription_id', 'current_period_start', 'current_period_end', 'trial_end', 'canceled_at', 'created_at', 'updated_at')
        read_only_fields = ('organization', 'stripe_customer_id', 'stripe_subscription_id',
                           'current_period_start', 'current_period_end')

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ('id', 'organization', 'subscription', 'stripe_invoice_id', 'amount', 'currency', 'status', 'period_start', 'period_end', 'paid_at', 'created_at', 'updated_at')
        read_only_fields = ('organization',)

class UsageEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageEvent
        fields = ('id', 'organization', 'user', 'event_type', 'quantity', 'metadata', 'created_at', 'updated_at')
        read_only_fields = ('organization',)

class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]
    queryset = Plan.objects.filter(is_active=True).order_by('sort_order')

class SubscriptionView(generics.RetrieveUpdateAPIView):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated, IsOrgOwner]

    def get_object(self):
        org = self.request.org
        obj, _ = Subscription.objects.get_or_create(organization=org)
        if not obj.plan:
            free = Plan.objects.filter(slug='free').first()
            if free:
                obj.plan = free
                obj.save()
        return obj

    def perform_update(self, serializer):
        instance = serializer.save()
        from tasks.billing_tasks import sync_subscription_to_stripe
        sync_subscription_to_stripe.delay(str(instance.id))

class SubscriptionCancelView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsOrgOwner]

    def post(self, request):
        sub = Subscription.objects.filter(organization=request.org).first()
        if sub:
            sub.status = 'canceled'
            sub.canceled_at = __import__('django.utils.timezone', fromlist=['now']).now()
            sub.save(update_fields=['status', 'canceled_at'])
        return Response({'status': 'canceled'})

class InvoiceViewSet(OrganizationFilterMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    search_fields = ['stripe_invoice_id']
    ordering_fields = ['created_at', 'amount', 'status']
    filterset_fields = ['status']

    def get_queryset(self):
        return super().get_queryset().select_related('organization', 'subscription', 'subscription__plan')

class UsageView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get(self, request):
        org = request.org
        current_period = Subscription.objects.filter(organization=org).first()
        if current_period and current_period.current_period_start:
            usage = UsageEvent.objects.filter(
                organization=org,
                created_at__gte=current_period.current_period_start,
            ).values('event_type').annotate(total=Sum('quantity'))
        else:
            usage = UsageEvent.objects.filter(organization=org).values('event_type').annotate(total=Sum('quantity'))
        return Response(list(usage))

class StripeWebhookView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        import stripe
        from django.conf import settings
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return Response({'error': 'Invalid payload'}, status=400)
        except stripe.error.SignatureVerificationError:
            return Response({'error': 'Invalid signature'}, status=400)

        from tasks.billing_tasks import handle_stripe_webhook
        handle_stripe_webhook.delay(event['type'], event['data']['object'])
        return Response({'status': 'received'})
