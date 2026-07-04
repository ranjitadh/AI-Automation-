import logging
import httpx
import json
import os
import tempfile
from celery import shared_task, chain
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import default_storage
from django.utils import timezone
from apps.jobs.models import Job
from apps.applications.models import Application
from apps.resumes.models import Resume, ResumeVersion
from apps.pipeline.models import PipelineRun

logger = logging.getLogger(__name__)
MAX_LOG_CHARS = 3000


def _log(run, msg, fail=False):
    if run:
        if fail:
            run.status = 'failed'
        run.log = (run.log or '') + msg + '\n'
        run.save(update_fields=['status', 'log'])


def _resolve_resume_path(version) -> str:
    if not version or not version.file:
        return None
    try:
        if hasattr(version.file, 'file') and hasattr(version.file.file, 'path'):
            path = version.file.file.path
            if os.path.exists(path):
                return path
    except Exception:
        pass
    try:
        storage_path = version.file.name
        if default_storage.exists(storage_path):
            suffix = os.path.splitext(storage_path)[1] or '.pdf'
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(default_storage.open(storage_path).read())
            tmp.close()
            return tmp.name
    except Exception:
        pass
    return None


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
    run.stage, run.status = 'research', 'running'
    run.save(update_fields=['stage', 'status'])
    job = run.job
    if job.job_description_url:
        try:
            r = httpx.get(job.job_description_url, timeout=10.0, follow_redirects=True)
            if r.status_code < 400:
                _log(run, f"Fetched job description ({len(r.text)} chars)")
        except Exception:
            logger.warning(f"Failed to fetch job URL: {job.job_description_url}")
            _log(run, "Failed to fetch job description", fail=True)
    return run_id


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
)
def task_analyze_fit_and_decide(run_id, campaign_id=None):
    try:
        run = PipelineRun.objects.get(id=run_id)
    except ObjectDoesNotExist:
        logger.error(f"PipelineRun {run_id} not found")
        return None
    run.stage = 'analysis'
    run.save(update_fields=['stage'])

    job = run.job
    org = run.organization
    user = None

    from apps.campaigns.models import Campaign
    campaign = None
    if campaign_id:
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            user = campaign.created_by
        except ObjectDoesNotExist:
            pass
    if not user:
        from apps.accounts.models import Organization
        org_obj = Organization.objects.get(id=org.id) if org else None
        if org_obj:
            user = org_obj.owner if hasattr(org_obj, 'owner') else None

    if not user:
        _log(run, "No user found for pipeline", fail=True)
        return None

    from apps.ai.matching_engine import (
        build_job_data_from_model, load_candidate_profile,
        analyze_job_match, calibrate_experience, decide_application,
    )

    job_data = build_job_data_from_model(job)
    candidate_data = load_candidate_profile(user, org)
    resume_data = candidate_data.get('resume', {})
    goals = candidate_data.get('goals', {})

    threshold = 70
    auto_apply = False
    if campaign:
        threshold = campaign.min_fit_score or 70
        auto_apply = campaign.auto_apply

    _log(run, f"Analyzing fit for {job.title} @ {job.company.name}...")
    job_match = analyze_job_match(
        job_data, candidate_data,
        organization_id=str(org.id),
        user_id=str(user.id),
    )

    if not job_match or 'fit_score' not in job_match:
        _log(run, "Fit analysis failed - no valid result", fail=True)
        return None

    fit_score = job_match.get('fit_score', 0)

    candidate_years = float(resume_data.get('years_of_experience', 0)) if resume_data else 0
    calibration = calibrate_experience(
        job_seniority=job.seniority or '',
        candidate_seniority=resume_data.get('seniority_level', '') if resume_data else '',
        candidate_years=candidate_years,
        job_years_required=None,
        job_data=job_data,
        resume_data=resume_data,
        organization_id=str(org.id),
        user_id=str(user.id),
    )

    decision = decide_application(
        job_match, calibration,
        threshold=threshold,
        auto_apply=auto_apply,
        user=user,
        organization=org,
        job=job,
    )

    run.decision = decision.decision if decision else 'unknown'
    run.fit_score = fit_score
    reasoning = job_match.get('reasoning', '')

    if 'Salary:' in reasoning:
        _log(run, "Salary throttle active")
    if 'Competition:' in reasoning:
        _log(run, "Competitive analysis active")

    try:
        from apps.ai.salary_throttle_engine import compute_throttle
        from apps.ai.competitive_analysis_engine import score_competitiveness

        goals_data = candidate_data.get('goals', {})
        throttle_info = compute_throttle(
            target_salary_min=goals_data.get('target_salary_min'),
            target_salary_max=goals_data.get('target_salary_max'),
            job_salary_min=job.salary_min,
            job_salary_max=job.salary_max,
            job_salary_period=job.salary_period,
        )
        run.throttle_factor = throttle_info.get('throttle_factor')
        run.bid_score = throttle_info.get('bid_score')

        comp_info = score_competitiveness(
            posted_at=job.posted_at,
            applicant_count=job.application_count,
            company_size=job.company.size if job.company else None,
            location=job.location,
            remote=job.remote,
        )
        run.competitiveness_score = comp_info.get('competitiveness_score')
    except Exception:
        pass

    run.save(update_fields=[
        'decision', 'fit_score', 'throttle_factor',
        'bid_score', 'competitiveness_score', 'log',
    ])

    _log(run, f"Fit score: {fit_score}/100 — Decision: {run.decision}")
    throttle_log = []
    if run.throttle_factor is not None:
        throttle_log.append(f"throttle={run.throttle_factor}")
    if run.bid_score is not None:
        throttle_log.append(f"bid={run.bid_score}")
    if run.competitiveness_score is not None:
        throttle_log.append(f"competition={run.competitiveness_score}")
    if throttle_log:
        _log(run, f"Pipeline signals: {', '.join(throttle_log)}")
    _log(run, f"Skills: {job_match.get('skill_match_score', 0)}% | Experience: {job_match.get('experience_match_score', 0)}% | Seniority: {job_match.get('seniority_match_score', 0)}% | Industry: {job_match.get('industry_match_score', 0)}%")

    strengths = reasoning[:300]
    if strengths:
        _log(run, f"Assessment: {strengths}")

    if decision and decision.decision in ('reject',):
        _log(run, f"Auto-rejected: {decision.auto_reject_reason or 'Fit score below threshold'}")
        run.status = 'done'
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'completed_at'])
        return None

    if decision and decision.decision == 'review':
        _log(run, "Flagged for review — overqualification/underqualification risk")
        run.status = 'done'
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'completed_at'])
        return None

    return (run_id, fit_score, calibration, job_data, candidate_data, decision, auto_apply)


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
)
def task_adapt_resume(task_input):
    if task_input is None:
        return None
    run_id, fit_score, calibration, job_data, candidate_data, decision, auto_apply = task_input

    try:
        run = PipelineRun.objects.get(id=run_id)
    except ObjectDoesNotExist:
        logger.error(f"PipelineRun {run_id} not found")
        return None
    run.stage = 'resume_adaptation'
    run.save(update_fields=['stage'])

    job = run.job
    org = run.organization

    from apps.ai.resume_adaptation_engine import adapt_resume, create_resume_version

    resume = Resume.objects.filter(organization=org, is_active=True).first()
    if not resume:
        _log(run, "No active resume found", fail=True)
        return None

    resume_data = {
        "summary": resume.summary,
        "skills": resume.skills or [],
        "experience": resume.experience or [],
        "education": resume.education or [],
        "certifications": resume.certifications or [],
        "years_of_experience": float(resume.years_of_experience) if resume.years_of_experience else 0,
        "seniority_level": resume.seniority_level,
    }

    _log(run, "Adapting resume for this job...")
    adapted = adapt_resume(
        resume_data, job_data, calibration,
        organization_id=str(org.id),
    )

    if not adapted or not adapted.get('adapted_summary'):
        _log(run, "Resume adaptation failed", fail=True)
        return None

    if adapted.get('_has_fabrication'):
        _log(run, f"Resume fabrication detected — blocking: {adapted.get('truthfulness_warnings', [])}", fail=True)
        return None

    version = create_resume_version(resume, job, adapted, org)
    if version is None:
        _log(run, "Resume version creation failed (fabrication check)", fail=True)
        return None

    _log(run, f"Resume adapted — version {version.version_number}, estimated ATS: {adapted.get('ats_score_estimate', 0)}%")

    return (run_id, fit_score, job_data, candidate_data, version, auto_apply)


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
)
def task_generate_cover_letter(task_input):
    if task_input is None:
        return None
    run_id, fit_score, job_data, candidate_data, version, auto_apply = task_input

    try:
        run = PipelineRun.objects.get(id=run_id)
    except ObjectDoesNotExist:
        logger.error(f"PipelineRun {run_id} not found")
        return None
    run.stage = 'generation'
    run.save(update_fields=['stage'])

    job = run.job
    org = run.organization

    from apps.ai.humanization_engine import generate_humanized_cover_letter

    _log(run, "Generating humanized cover letter...")
    letter_result = generate_humanized_cover_letter(
        job_data, candidate_data,
        organization_id=str(org.id),
    )

    cover_text = ""
    if letter_result:
        cover_text = letter_result.get('full_text', '') or letter_result.get('body', '')
        word_count = letter_result.get('word_count', 0)
        _log(run, f"Cover letter generated ({word_count} words)")

    if not cover_text:
        _log(run, "Cover letter generation failed — proceeding with placeholder")

    return (run_id, fit_score, job, org, version, cover_text, auto_apply)


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2},
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    soft_time_limit=120,
    time_limit=300,
    acks_late=True,
)
def task_evaluate_quality(task_input):
    if task_input is None:
        return None
    run_id, fit_score, job, org, version, cover_text, auto_apply = task_input

    try:
        run = PipelineRun.objects.get(id=run_id)
    except ObjectDoesNotExist:
        logger.error(f"PipelineRun {run_id} not found")
        return None
    run.stage = 'quality_check'
    run.save(update_fields=['stage'])

    from apps.ai.recruiter_simulation_engine import simulate_recruiter_perspectives
    from apps.ai.application_quality_engine import evaluate_application_quality

    resume = Resume.objects.filter(organization=org, is_active=True).first()
    resume_data = {}
    if resume:
        resume_data = {
            'summary': resume.summary or '',
            'skills': resume.skills or [],
            'experience': resume.experience or [],
            'years_of_experience': float(resume.years_of_experience) if resume.years_of_experience else 0,
            'seniority_level': resume.seniority_level or '',
        }
    profile_data = {}

    job_for_quality = {
        'title': job.title,
        'company': job.company.name if job.company else '',
        'description': job.description or '',
        'required_skills': job.requirements or [],
        'seniority_level': job.seniority or '',
        'location': job.location or '',
        'salary_min': job.salary_min,
        'salary_max': job.salary_max,
    }

    quality = evaluate_application_quality(
        resume_data=resume_data,
        cover_letter_text=cover_text or '',
        screening_answers=[],
        profile_data=profile_data,
        job_data=job_for_quality,
    )
    quality_score = quality.get('application_quality_score', 50)
    run.quality_score = quality_score
    run.save(update_fields=['quality_score'])

    sim = simulate_recruiter_perspectives(
        resume_data=resume_data,
        cover_letter_text=cover_text or '',
        screening_answers=[],
        profile_data=profile_data,
        job_data=job_for_quality,
    )
    interview_prob = sim.get('interview_probability', 0)
    should_submit = quality.get('should_submit', True)

    _log(run, f"Quality: {quality_score}/100 | Interview prob: {interview_prob:.0%} | Submit: {should_submit}")

    if not should_submit and quality_score < 40:
        _log(run, f"Low quality score ({quality_score}) — proceeding with caution")
    elif interview_prob < 0.1 and quality_score < 50:
        _log(run, f"Low interview probability ({interview_prob:.0%}) — lowering expectations")

    return (run_id, fit_score, job, org, version, cover_text, auto_apply)


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
)
def task_create_application(task_input, campaign_id=None):
    if task_input is None:
        return None
    run_id, fit_score, job, org, version, cover_text, auto_apply = task_input

    try:
        run = PipelineRun.objects.get(id=run_id)
    except ObjectDoesNotExist:
        logger.error(f"PipelineRun {run_id} not found")
        return None

    app = Application.objects.create(
        organization=org,
        job=job,
        resume=version.resume if version else None,
        resume_version=version,
        cover_letter=None,
        status='approved' if auto_apply else 'queued',
        dispatch_status='pending',
    )

    run.application_id = str(app.id)
    if version:
        run.resume_version_id = str(version.id)
    run.save(update_fields=['application_id', 'resume_version_id'])

    _log(run, f"Application {app.id} created ({'auto-apply' if auto_apply else 'queued for review'})")

    if not auto_apply:
        run.status = 'done'
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'completed_at'])
        return None

    return (run_id, app.id, version, cover_text, job)


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=600,
    time_limit=1200,
    acks_late=True,
)
def task_validate_and_dispatch(task_input):
    if task_input is None:
        return False
    run_id, app_id, version, cover_text, job = task_input

    try:
        run = PipelineRun.objects.get(id=run_id)
    except ObjectDoesNotExist:
        logger.error(f"PipelineRun {run_id} not found")
        return False
    run.stage = 'validation'
    run.save(update_fields=['stage'])

    from apps.ai.validation_engine import validate_before_submission
    from apps.ai.consistency_engine import verify_application_consistency

    from apps.ai.matching_engine import load_candidate_profile

    candidate_data_full = load_candidate_profile(app.applicant, app.organization) if app.applicant_id else {}
    profile_data = candidate_data_full
    candidate_resume_data = candidate_data_full.get('resume', {})

    validation_data = {
        'resume': {'adapted_text': version.optimized_text if version else ''},
        'cover_letter': cover_text,
        'answers': [],
        'fit_score': 70,
        'threshold': 70,
        'profile': profile_data,
        'job': {
            'title': job.title,
            'company': job.company.name if job.company else '',
            'location': job.location or '',
            'remote': job.remote,
            'salary_min': job.salary_min,
            'salary_max': job.salary_max,
            'requirements': job.requirements or [],
            'seniority': job.seniority or '',
        },
    }

    _log(run, "Validating application before submission...")
    validation_result = validate_before_submission(validation_data)

    consistency = verify_application_consistency(
        resume_data=candidate_resume_data,
        cover_letter_text=cover_text,
        screening_answers=[],
        profile_data=profile_data,
        job_data=validation_data['job'],
    )

    if not consistency.get('is_consistent', True):
        _log(run, f"Consistency check failed: {consistency.get('contradictions', [])}")
        validation_result['decision'] = 'block'
        validation_result['blockers'].extend(consistency.get('contradictions', []))

    decision = validation_result.get('decision', 'queue_for_review')
    _log(run, f"Validation: {decision} ({len(validation_result.get('warnings', []))} warnings, {len(validation_result.get('blockers', []))} blockers)")

    if decision != 'submit':
        _log(run, f"Validation blocked — {json.dumps(validation_result.get('blockers', []) + validation_result.get('warnings', []))}")
        try:
            app = Application.objects.get(id=app_id)
            app.status = 'queued'
            app.dispatch_status = 'pending'
            app.save(update_fields=['status', 'dispatch_status'])
        except ObjectDoesNotExist:
            pass
        run.status = 'done'
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'completed_at'])
        return False

    try:
        app = Application.objects.get(id=app_id)
    except ObjectDoesNotExist:
        _log(run, f"Application {app_id} not found", fail=True)
        return False

    app.status = 'applying'
    app.dispatch_status = 'running'
    app.save(update_fields=['status', 'dispatch_status'])

    _log(run, "Dispatching via Playwright automation...")
    return _run_playwright_submission(app, job, run, version, cover_text)


def _run_playwright_submission(app, job, run, version, cover_text):
    from apps.automation.runner import run_automation

    resume_file_path = _resolve_resume_path(version)

    applicant_info = {
        'name': app.applicant.get_full_name() if app.applicant_id else '',
        'email': app.applicant.email if app.applicant_id else '',
        'phone': '',
        'linkedin': '',
        'website': '',
        'resume_path': resume_file_path,
    }

    success, logs, screenshot_path = run_automation(job, cover_text, applicant_info)

    log_text = "\n".join(logs)
    app.dispatch_log = log_text
    app.dispatch_attempts = (app.dispatch_attempts or 0) + 1

    captcha_detected = any('CAPTCHA' in line for line in logs)
    if captcha_detected:
        _log(run, "CAPTCHA was detected during submission", fail=True)

    if screenshot_path:
        from apps.common.models import FileUpload
        try:
            fu = FileUpload.objects.create(
                organization=app.organization,
                file=screenshot_path,
                uploaded_by=app.applicant,
            )
            app.screenshot_after = fu
        except Exception:
            pass

    if success:
        app.status = 'submitted'
        app.dispatch_status = 'success'
        app.submitted_at = timezone.now()
        _log(run, "Application submitted successfully!")
    else:
        app.status = 'failed'
        app.dispatch_status = 'failed'
        if captcha_detected:
            _log(run, "CAPTCHA blocked submission — application will not retry")
        else:
            _log(run, f"Application submission failed — see dispatch log", fail=True)

    app.last_dispatched_at = timezone.now()
    app.save()

    if run:
        run.stage = 'submission'
        run.status = 'done' if success else 'failed'
        run.completed_at = timezone.now()
        run.log = (run.log or '') + f"\nDispatch:\n{log_text}"
        run.save()

    return success


def start_pipeline_for_job(job_id, campaign_id=None, org_id=None):
    try:
        job = Job.objects.select_related('source', 'company').get(id=job_id)
    except ObjectDoesNotExist:
        logger.error(f"Job {job_id} not found")
        return None
    org_id = org_id or (job.source.organization_id if job.source else None)
    if not org_id:
        logger.error(f"Job {job_id} has no source organization")
        return None

    org_model = job.source.organization if job.source else None
    from apps.accounts.models import Organization
    try:
        org = Organization.objects.get(id=org_id)
    except ObjectDoesNotExist:
        logger.error(f"Organization {org_id} not found")
        return None

    run = PipelineRun.objects.create(job=job, organization_id=org_id)

    auto = False
    if campaign_id:
        from apps.campaigns.models import Campaign
        try:
            c = Campaign.objects.get(id=campaign_id)
            if c.auto_apply:
                auto = True
        except ObjectDoesNotExist:
            logger.warning(f"Campaign {campaign_id} not found")

    tasks = [
        task_research_job.s(run.id),
        task_analyze_fit_and_decide.s(campaign_id=campaign_id),
        task_adapt_resume.s(),
        task_generate_cover_letter.s(),
        task_evaluate_quality.s(),
        task_create_application.s(campaign_id=campaign_id),
    ]
    if auto:
        tasks.append(task_validate_and_dispatch.s())

    chain(*tasks).apply_async()
    return run.id
