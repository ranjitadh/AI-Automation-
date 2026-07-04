from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import QuestionBank, QuestionAnswer
from apps.common.mixins import OrganizationFilterMixin
from apps.common.permissions import IsOrgMember

class QuestionBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionBank
        fields = ('id', 'organization', 'question', 'category', 'is_system', 'is_active', 'created_at', 'updated_at')

class QuestionAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question', read_only=True)
    question_category = serializers.CharField(source='question.category', read_only=True)

    class Meta:
        model = QuestionAnswer
        fields = ('id', 'organization', 'user', 'question', 'question_text', 'question_category', 'answer', 'is_ai_generated', 'is_approved', 'use_count', 'created_at', 'updated_at')
        read_only_fields = ('user', 'organization', 'use_count')

class QuestionBankViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QuestionBankSerializer
    permission_classes = [IsAuthenticated]
    queryset = QuestionBank.objects.filter(is_active=True)
    search_fields = ['question', 'category']
    filterset_fields = ['category', 'is_system']

class QuestionAnswerViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    queryset = QuestionAnswer.objects.all()
    serializer_class = QuestionAnswerSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    search_fields = ['question__question', 'answer']
    ordering_fields = ['created_at']
    filterset_fields = ['question', 'is_ai_generated', 'is_approved']

    def get_queryset(self):
        return super().get_queryset().select_related('organization', 'user', 'question')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, organization=self.request.org)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        question_id = request.data.get('question')
        job_id = request.data.get('job')
        if not question_id:
            return Response({'error': 'question required'}, status=400)
        from tasks.question_tasks import generate_answer_task
        task = generate_answer_task.delay(question_id, job_id, str(request.user.id), str(request.org.id))
        return Response({'status': 'generating', 'task_id': task.id})
