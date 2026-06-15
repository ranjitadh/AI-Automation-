import logging
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

def create_notification(org_id, user_id, type, title, body=None, data=None, channel='in_app'):
    from .models import Notification
    notification = Notification.objects.create(
        organization_id=org_id,
        user_id=user_id,
        type=type,
        title=title,
        body=body or title,
        data=data or {},
        channel=channel,
    )
    if channel != 'in_app':
        from tasks.notification_tasks import send_notification_task
        send_notification_task.delay(str(notification.id))
    return notification

def send_email(notification):
    if not settings.EMAIL_HOST:
        logger.warning("Email not configured")
        return False
    try:
        send_mail(
            subject=notification.title,
            message=notification.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.user.email] if notification.user else [settings.ADMIN_EMAIL],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False

def send_slack(notification):
    webhook = getattr(settings, 'SLACK_WEBHOOK_URL', '')
    if not webhook:
        return False
    try:
        import httpx
        httpx.post(webhook, json={'text': f"*{notification.title}*\n{notification.body}"}, timeout=5)
        return True
    except Exception as e:
        logger.error(f"Slack send failed: {e}")
        return False

def send_discord(notification):
    webhook = getattr(settings, 'DISCORD_WEBHOOK_URL', '')
    if not webhook:
        return False
    try:
        import httpx
        httpx.post(webhook, json={'content': f"**{notification.title}**\n{notification.body}"}, timeout=5)
        return True
    except Exception as e:
        logger.error(f"Discord send failed: {e}")
        return False

def send_webhook(notification):
    webhooks = notification.organization.webhooks.filter(is_active=True)
    for webhook in webhooks:
        try:
            import httpx, json
            payload = {
                'event': notification.type,
                'title': notification.title,
                'body': notification.body,
                'data': notification.data,
                'timestamp': notification.created_at.isoformat(),
            }
            sig = webhook.secret
            headers = {'Content-Type': 'application/json'}
            if sig:
                import hmac, hashlib
                signature = hmac.new(sig.encode(), json.dumps(payload).encode(), hashlib.sha256).hexdigest()
                headers['X-Webhook-Signature'] = signature
            httpx.post(webhook.url, json=payload, headers=headers, timeout=10)
            webhook.last_success_at = __import__('django.utils.timezone', fromlist=['now']).now()
        except Exception as e:
            webhook.last_failure_at = __import__('django.utils.timezone', fromlist=['now']).now()
            webhook.failure_count += 1
            logger.error(f"Webhook failed for {webhook.url}: {e}")
        webhook.save(update_fields=['last_success_at', 'last_failure_at', 'failure_count'])
