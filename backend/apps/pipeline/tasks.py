import logging
import httpx
from celery import shared_task, chain
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from apps.jobs.models import Job
from apps.applications.models import Application
from apps.resumes.models import Resume
from apps.pipeline.models import PipelineRun
from apps.pipeline.utils import analyze_job_fit, generate_cover_letter

logger = logging.getLogger(__name__)

def _log(run, msg, fail=False):
    if run:
        if fail: run.status = 'failed'
        run.log = (run.log or '') + msg + '\n'
        run.save(update_fields=['status', 'log'])

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=120,
    time_limit=300,
    acks_late=True,
)
def task_research_job(run_id):
    try:
        run = PipelineRun.objects.get(id=run_id)
    except ObjectDoesNotExist:
        logger.error(f"PipelineRun {run_id} not found")
        return None
    run.stage, run.status = 'research', 'running'; run.save(update_fields=['stage', 'status'])
    job = run.job
    if job.job_description_url:
        try:
            r = httpx.get(job.job_description_url, timeout=10.0, follow_redirects=True)
            if r.status_code < 400:
                if not job.job_description_text: job.job_description_text = r.text[:10000]
                job.has_application_form = True
        except Exception:
            logger.warning(f"Failed to fetch job URL: {job.job_description_url}")
            job.has_application_form = False
    job.save(update_fields=['has_application_form', 'job_description_text'])
    return run_id

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=120,
    time_limit=300,
    acks_late=True,
)
def task_analyze_fit(run_id):
    try:
        run = PipelineRun.objects.get(id=run_id)
    except ObjectDoesNotExist:
        logger.error(f"PipelineRun {run_id} not found")
        return None
    run.stage = 'analysis'; run.save(update_fields=['stage'])
    job = run.job
    d = analyze_job_fit(job)
    job.fit_score = d.get('score', 0)
    job.analysis_notes = d
    job.save(update_fields=['fit_score', 'analysis_notes'])
    return run_id

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=120,
    time_limit=300,
    acks_late=True,
)
def task_generate_cover_letter(run_id, campaign_id=None):
    try:
        run = PipelineRun.objects.get(id=run_id)
    except ObjectDoesNotExist:
        logger.error(f"PipelineRun {run_id} not found")
        return None
    run.stage = 'generation'; run.save(update_fields=['stage'])
    job, resume = run.job, Resume.objects.filter(is_active=True).first()
    data = generate_cover_letter(job, resume_text=(resume.parsed_text or "") if resume else "", skills=resume.skills if resume else [])
    app = Application.objects.create(job=job, campaign_id=campaign_id, cover_letter=data.get('cover_letter', ''))

    auto = job.auto_apply
    if campaign_id:
        from apps.campaigns.models import Campaign
        try:
            c = Campaign.objects.get(id=campaign_id)
            if c.auto_apply: auto = True
        except ObjectDoesNotExist:
            logger.warning(f"Campaign {campaign_id} not found in task_generate_cover_letter")

    if not auto:
        run.status, run.completed_at = 'done', timezone.now()
        run.save(update_fields=['status', 'completed_at'])
    return str(app.id)

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=600,
    time_limit=1200,
    acks_late=True,
)
def task_dispatch_application_auto(application_id, run_id=None):
    from apps.pipeline.playwright_utils import run_auto_apply_model
    try:
        app = Application.objects.get(id=application_id)
    except ObjectDoesNotExist:
        logger.error(f"Application {application_id} not found")
        return False
    logs = []
    app.dispatch_status = 'running'; app.save(update_fields=['dispatch_status'])
    run = PipelineRun.objects.filter(id=run_id).first() if run_id else None
    if run: run.stage = 'submission'; run.save(update_fields=['stage'])

    success, play_logs, ss_path = run_auto_apply_model(app.job, app.cover_letter)
    logs.extend(play_logs)
    if ss_path: app.screenshot = ss_path

    if success:
        app.status, app.submitted_at, app.dispatch_status = 'submitted', timezone.now(), 'success'
    else:
        app.dispatch_status = 'failed'
    app.dispatch_log = "\n".join(logs)
    app.save()

    if run:
        run.status = 'done' if success else 'failed'
        run.completed_at = timezone.now()
        run.log = (run.log or '') + "\nDispatch:\n" + "\n".join(logs)
        run.save()
    return success

def start_pipeline_for_job(job_id, campaign_id=None, org_id=None):
    try:
        job = Job.objects.select_related('source').get(id=job_id)
    except ObjectDoesNotExist:
        logger.error(f"Job {job_id} not found")
        return None
    org_id = org_id or (job.source.organization_id if job.source else None)
    if not org_id:
        logger.error(f"Job {job_id} has no source organization")
        return None
    run = PipelineRun.objects.create(job=job, organization_id=org_id)

    auto = job.auto_apply
    if campaign_id:
        from apps.campaigns.models import Campaign
        try:
            c = Campaign.objects.get(id=campaign_id)
            if c.auto_apply: auto = True
        except ObjectDoesNotExist:
            logger.warning(f"Campaign {campaign_id} not found")

    tasks = [task_research_job.s(run.id), task_analyze_fit.s(), task_generate_cover_letter.s(campaign_id=campaign_id)]
    if auto: tasks.append(task_dispatch_application_auto.s(run_id=run.id))
    chain(*tasks).apply_async()
    return run.id
