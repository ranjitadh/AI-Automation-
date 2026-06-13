import httpx
from celery import shared_task, chain
from django.utils import timezone
from apps.businesses.models import Business
from apps.outreach.models import OutreachEmail
from apps.pipeline.models import PipelineRun
from apps.pipeline.utils import analyze_business_presence, generate_outreach_email

@shared_task
def task_research_business(run_id):
    try:
        run = PipelineRun.objects.get(id=run_id)
        run.stage = 'research'
        run.status = 'running'
        run.save()

        business = run.business
        
        # Simple research: Check if website is reachable if provided
        if business.website_url:
            try:
                response = httpx.get(business.website_url, timeout=5.0)
                business.has_website = response.status_code < 400
            except:
                business.has_website = False
        else:
            business.has_website = False
            
        business.save()
        return run_id
    except Exception as e:
        if 'run' in locals():
            run.status = 'failed'
            run.log = f"Research failed: {str(e)}"
            run.save()
        raise e

@shared_task
def task_analyze_presence(run_id):
    try:
        run = PipelineRun.objects.get(id=run_id)
        run.stage = 'analysis'
        run.save()

        business = run.business
        analysis_data = analyze_business_presence(business)
        
        business.digital_score = analysis_data.get('score', 0)
        business.analysis_notes = analysis_data
        business.save()
        
        return run_id
    except Exception as e:
        run.status = 'failed'
        run.log = f"Analysis failed: {str(e)}"
        run.save()
        raise e

@shared_task
def task_generate_email(run_id, campaign_id=None):
    try:
        run = PipelineRun.objects.get(id=run_id)
        run.stage = 'generation'
        run.save()

        business = run.business
        email_data = generate_outreach_email(business)
        
        email = OutreachEmail.objects.create(
            business=business,
            campaign_id=campaign_id,
            subject=email_data.get('subject', 'Quick question'),
            email_body=email_data.get('email', 'Hi, I would love to connect.')
        )
        
        # Check if we are running in auto_apply mode or manual
        auto_apply = business.auto_apply
        if campaign_id:
            from apps.campaigns.models import Campaign
            try:
                campaign = Campaign.objects.get(id=campaign_id)
                if campaign.auto_apply:
                    auto_apply = True
            except Campaign.DoesNotExist:
                pass

        if not auto_apply:
            run.status = 'done'
            run.completed_at = timezone.now()
            run.save()
        
        return str(email.id)
    except Exception as e:
        run.status = 'failed'
        run.log = f"Email generation failed: {str(e)}"
        run.save()
        raise e

@shared_task
def task_dispatch_outreach_direct(email_id, run_id=None):
    from apps.pipeline.playwright_utils import run_auto_apply_model
    from django.core.mail import send_mail
    from django.conf import settings
    
    logs = []
    logs.append(f"[Dispatcher] Starting direct outreach dispatch for email {email_id}...")
    
    try:
        email = OutreachEmail.objects.get(id=email_id)
        email.dispatch_status = 'running'
        email.save()
        
        run = None
        if run_id:
            try:
                run = PipelineRun.objects.get(id=run_id)
                run.stage = 'dispatch'
                run.save()
            except PipelineRun.DoesNotExist:
                pass
                
        business = email.business
        agency_info = {
            'name': getattr(settings, 'AGENCY_NAME', 'Your Agency'),
            'email': getattr(settings, 'AGENCY_EMAIL', 'hello@youragency.com'),
            'phone': getattr(settings, 'AGENCY_PHONE', '+1-234-567-8900'),
        }
        
        dispatched = False
        screenshot_file = None
        
        # Mode 1: Direct SMTP Email
        if business.email:
            logs.append(f"[Mode 1/2] Direct email found: {business.email}. Attempting SMTP dispatch...")
            try:
                send_mail(
                    subject=email.subject,
                    message=email.email_body,
                    from_email=agency_info['email'],
                    recipient_list=[business.email],
                    fail_silently=False,
                )
                logs.append(f"[Success] Email successfully sent via SMTP to {business.email}")
                dispatched = True
            except Exception as mail_err:
                logs.append(f"[Warning] SMTP dispatch failed: {str(mail_err)}. Trying web contact form alternative...")
                
        # Mode 2: Playwright Web Form Submitter
        if not dispatched and business.website_url:
            logs.append(f"[Mode 2/2] Website URL found: {business.website_url}. Initiating Playwright form filler...")
            success, playwright_logs, screenshot_path = run_auto_apply_model(
                website_url=business.website_url,
                subject=email.subject,
                body=email.email_body,
                agency_info=agency_info
            )
            logs.extend(playwright_logs)
            
            if success:
                dispatched = True
                if screenshot_path:
                    email.screenshot = screenshot_path
            elif screenshot_path:
                email.screenshot = screenshot_path
                
        if dispatched:
            email.status = 'sent'
            email.sent_at = timezone.now()
            email.dispatch_status = 'success'
            email.dispatch_log = "\n".join(logs)
            email.save()
            
            if run:
                run.status = 'done'
                run.completed_at = timezone.now()
                run.log = f"Outreach successfully dispatched!\n{run.log or ''}\n\n=== DISPATCH LOGS ===\n" + "\n".join(logs)
                run.save()
                
            return True
        else:
            email.dispatch_status = 'failed'
            email.dispatch_log = "\n".join(logs)
            email.save()
            
            if run:
                run.status = 'failed'
                run.log = f"Outreach dispatch failed.\n{run.log or ''}\n\n=== DISPATCH LOGS ===\n" + "\n".join(logs)
                run.save()
                
            return False
            
    except Exception as e:
        err_msg = f"Fatal error in dispatch task: {str(e)}"
        logs.append(err_msg)
        if 'email' in locals() and email:
            email.dispatch_status = 'failed'
            email.dispatch_log = "\n".join(logs)
            email.save()
        if 'run' in locals() and run:
            run.status = 'failed'
            run.log = f"Outreach dispatch crashed.\n{run.log or ''}\n\n" + err_msg
            run.save()
        raise e

def start_pipeline_for_business(business_id, campaign_id=None):
    business = Business.objects.get(id=business_id)
    run = PipelineRun.objects.create(business=business)
    
    # Check if auto_apply is enabled at the campaign or business level
    auto_apply = business.auto_apply
    if campaign_id:
        from apps.campaigns.models import Campaign
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            if campaign.auto_apply:
                auto_apply = True
        except Campaign.DoesNotExist:
            pass
            
    tasks_list = [
        task_research_business.s(run.id),
        task_analyze_presence.s(),
        task_generate_email.s(campaign_id=campaign_id)
    ]
    
    if auto_apply:
        tasks_list.append(task_dispatch_outreach_direct.s(run_id=run.id))
        
    # Execute as a Celery chain
    workflow = chain(*tasks_list)
    workflow.apply_async()
    return run.id
