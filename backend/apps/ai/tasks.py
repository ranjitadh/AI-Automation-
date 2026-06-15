import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2},
    retry_backoff=True,
    soft_time_limit=600,
    time_limit=1200,
    acks_late=True,
    queue='ai',
)
def task_ai_generate(task_type, system_prompt, user_prompt, **kwargs):
    from .gateway import generate
    return generate(
        task_type=task_type,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        **kwargs,
    )


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2},
    retry_backoff=True,
    soft_time_limit=600,
    time_limit=1200,
    acks_late=True,
    queue='ai',
)
def task_analyze_job(job_id, organization_id=None, user_id=None):
    from apps.jobs.models import Job
    from apps.resumes.models import Resume
    from .engines import analyze_fit

    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        return None

    job_data = {
        'title': job.title,
        'description': job.description,
        'requirements': job.requirements or [],
        'company': job.company.name if job.company else None,
        'location': job.location,
        'salary_min': job.salary_min,
        'salary_max': job.salary_max,
        'seniority': job.seniority,
    }

    # FIX: Filter resume by organization AND user instead of global .first()
    resume_filter = {'is_active': True}
    if organization_id:
        resume_filter['organization_id'] = organization_id
    if user_id:
        resume_filter['user_id'] = user_id
    resume = Resume.objects.filter(**resume_filter).first()
    resume_data = None
    if resume:
        resume_data = {
            'title': resume.title,
            'summary': resume.summary,
            'skills': resume.skills or [],
            'experience': resume.experience or [],
            'years_of_experience': resume.years_of_experience,
            'seniority_level': resume.seniority_level,
        }

    result = analyze_fit(
        job_data, resume_data,
        organization_id=organization_id,
        user_id=user_id,
    )
    return result


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='ai',
)
def task_generate_learning_insights(organization_id, user_id):
    from apps.applications.models import Application
    from .engines import extract_learning_insights
    from django.contrib.auth import get_user_model
    from apps.accounts.models import Organization

    user = get_user_model().objects.get(id=user_id)
    org = Organization.objects.get(id=organization_id)
    apps = Application.objects.filter(organization=org).values(
        'id', 'status', 'created_at', 'job__title', 'job__company__name'
    )[:100]

    return extract_learning_insights(user, org, list(apps))


@shared_task(
    soft_time_limit=120,
    time_limit=240,
    acks_late=True,
    queue='ai',
)
def task_decay_learning_confidence():
    """Periodic: decay all CareerMemory confidence values by 5% per day."""
    from .models import CareerMemory
    from .learning_engine import _decay_confidence
    updated = 0
    for memory in CareerMemory.objects.filter(confidence__gt=0.15):
        old_conf = memory.confidence
        new_conf = _decay_confidence(memory)
        if new_conf != old_conf:
            memory.confidence = new_conf
            memory.save(update_fields=['confidence', 'updated_at'])
            updated += 1
    logger.info(f"Decayed confidence for {updated} career memories")
    return updated


@shared_task(
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='ai',
)
def task_weekly_learning_digest_all():
    """Periodic: generate weekly learning digest for all active users."""
    from django.contrib.auth import get_user_model
    from apps.accounts.models import Organization, OrganizationMembership
    from .learning_engine import get_weekly_report

    User = get_user_model()
    digests = 0
    for org in Organization.objects.filter(is_active=True):
        admins = User.objects.filter(
            organization_memberships__organization=org,
            organization_memberships__role__in=['admin', 'owner'],
        )[:5]
        for user in admins:
            try:
                digest = get_weekly_report(user, org)
                if digest and digest.get('week_applications', 0) > 0:
                    logger.info(
                        f"Weekly digest for {user.email} in {org.name}: "
                        f"{digest.get('week_applications')} apps, "
                        f"{digest.get('week_interviews')} interviews"
                    )
                    digests += 1
            except Exception as e:
                logger.error(f"Digest failed for {user.email} in {org.name}: {e}")
    logger.info(f"Generated {digests} weekly digests")
    return digests


@shared_task(
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='analysis',
)
def task_analyze_pending_applications():
    """Periodic: analyze applications that haven't been scored yet."""
    from apps.applications.models import Application
    from .application_quality_engine import evaluate_application_quality

    pending = Application.objects.filter(
        quality_score__isnull=True,
        status__in=['submitted', 'pending'],
    ).select_related('job', 'resume')[:50]

    scored = 0
    for app in pending:
        try:
            result = evaluate_application_quality(app)
            if result and 'overall_score' in result:
                app.quality_score = result['overall_score']
                app.save(update_fields=['quality_score'])
                scored += 1
        except Exception as e:
            logger.error(f"Failed to score application {app.id}: {e}")
    logger.info(f"Scored {scored}/{pending.count()} pending applications")
    return scored


@shared_task(
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='cover_letter',
)
def task_generate_pending_cover_letters():
    """Periodic: generate cover letters for applications missing them."""
    from apps.applications.models import Application

    pending = Application.objects.filter(
        cover_letter_content__isnull=True,
        status='draft',
    ).select_related('job', 'resume')[:20]

    generated = 0
    for app in pending:
        try:
            from .services import generate_cover_letter
            job_data = {
                'title': app.job.title,
                'description': app.job.description,
                'company': app.job.company.name if app.job.company else None,
            }
            resume_data = {
                'summary': app.resume.summary,
                'skills': app.resume.skills or [],
                'experience': app.resume.experience or [],
            } if app.resume else {}
            result = generate_cover_letter(job_data, resume_data)
            if result and result.get('content'):
                app.cover_letter_content = result['content']
                app.save(update_fields=['cover_letter_content'])
                generated += 1
        except Exception as e:
            logger.error(f"Failed to generate cover letter for {app.id}: {e}")
    logger.info(f"Generated {generated}/{pending.count()} pending cover letters")
    return generated
