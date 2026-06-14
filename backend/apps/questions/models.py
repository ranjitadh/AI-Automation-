from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedMixin

class QuestionBank(TimeStampedMixin):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='question_bank', db_index=True)
    question = models.TextField()
    category = models.CharField(max_length=100, db_index=True)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'question']
        verbose_name_plural = 'question bank'
        unique_together = ['organization', 'question']

    def __str__(self):
        return self.question[:100]

class QuestionAnswer(TimeStampedMixin):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='question_answers', db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='question_answers', db_index=True)
    question = models.ForeignKey(QuestionBank, on_delete=models.CASCADE, related_name='answers', db_index=True)
    answer = models.TextField()
    is_ai_generated = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    use_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-use_count']
        unique_together = ['user', 'question']

    def __str__(self):
        return f"Answer: {self.question.question[:50]}"
