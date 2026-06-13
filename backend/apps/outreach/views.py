from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import OutreachEmail
from .serializers import OutreachEmailSerializer
from django.utils import timezone

class OutreachEmailViewSet(viewsets.ModelViewSet):
    queryset = OutreachEmail.objects.all().order_by('-generated_at')
    serializer_class = OutreachEmailSerializer
    filterset_fields = ['status', 'campaign']

    @action(detail=True, methods=['patch'])
    def mark_sent(self, request, pk=None):
        email = self.get_object()
        email.status = 'sent'
        email.sent_at = timezone.now()
        email.save()
        return Response({'status': 'marked as sent'})

    @action(detail=True, methods=['patch'])
    def mark_replied(self, request, pk=None):
        email = self.get_object()
        email.status = 'replied'
        email.reply_received = True
        email.reply_content = request.data.get('reply_content', '')
        email.save()
        return Response({'status': 'marked as replied'})

    @action(detail=True, methods=['post'])
    def dispatch_direct(self, request, pk=None):
        email = self.get_object()
        from apps.pipeline.tasks import task_dispatch_outreach_direct
        
        # Reset log and set state to running/pending
        email.dispatch_status = 'pending'
        email.dispatch_log = "[System] Scheduling automated direct apply dispatch..."
        email.save()
        
        # Trigger the celery task asynchronously
        task_dispatch_outreach_direct.delay(str(email.id))
        
        return Response({'status': 'direct dispatch scheduled', 'dispatch_status': email.dispatch_status})
