import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from apps.questions.models import QuestionBank, QuestionAnswer
from apps.questions.generators import generate_answer
from apps.jobs.models import Job

logger = logging.getLogger(__name__)

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='question',
)
def generate_answer_task(question_id, job_id=None, user_id=None, org_id=None):
    try:
        question = QuestionBank.objects.get(id=question_id)
    except ObjectDoesNotExist:
        logger.error(f"Question {question_id} not found")
        return None
    job = None
    if job_id:
        try:
            job = Job.objects.get(id=job_id)
        except ObjectDoesNotExist:
            logger.error(f"Job {job_id} not found")
    answer_text = generate_answer(question, job)
    if answer_text:
        answer, _ = QuestionAnswer.objects.update_or_create(
            user_id=user_id,
            question=question,
            defaults={
                'organization_id': org_id,
                'answer': answer_text,
                'is_ai_generated': True,
                'is_approved': False,
            }
        )
        return str(answer.id)
    return None
