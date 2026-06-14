import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from django.utils import timezone
from django.conf import settings
from cryptography.fernet import Fernet
from apps.automation.models import BrowserSession

logger = logging.getLogger(__name__)

def _get_fernet():
    return Fernet(settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY)

SESSION_EXPIRY_DAYS = 7

class SessionManager:
    def __init__(self, storage_path=None):
        self.storage_path = storage_path

    @staticmethod
    def save_session(context, session: BrowserSession):
        try:
            cookies = context.cookies()
            storage_state = context.storage_state() if hasattr(context, 'storage_state') else {}
            cookieless_data = {'storage_state': storage_state, 'saved_at': timezone.now().isoformat()}
            if cookies:
                f = _get_fernet()
                encrypted_cookies = f.encrypt(json.dumps(cookies).encode()).decode()
                cookieless_data['encrypted_cookies'] = encrypted_cookies
            session.session_data = cookieless_data
            session.last_used_at = timezone.now()
            session.save(update_fields=['session_data', 'last_used_at'])
            logger.info(f"Session saved for {session.platform}")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    @staticmethod
    def load_session(context, session: BrowserSession) -> bool:
        try:
            data = session.session_data or {}
            if not session.is_active:
                logger.warning(f"Session for {session.platform} is not active")
                return False
            last_used = session.last_used_at
            if last_used and (timezone.now() - last_used) > timedelta(days=SESSION_EXPIRY_DAYS):
                logger.warning(f"Session for {session.platform} expired")
                session.is_active = False
                session.status = 'expired'
                session.save(update_fields=['is_active', 'status'])
                return False
            encrypted_cookies = data.get('encrypted_cookies')
            if encrypted_cookies:
                f = _get_fernet()
                cookies = json.loads(f.decrypt(encrypted_cookies.encode()).decode())
                context.add_cookies(cookies)
                logger.info(f"Session loaded for {session.platform}")
                return True
            cookies = data.get('cookies', [])
            if cookies:
                context.add_cookies(cookies)
                logger.info(f"Session loaded for {session.platform}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return False

    @staticmethod
    def get_or_create_session(org_id, user_id, platform) -> BrowserSession:
        session, _ = BrowserSession.objects.get_or_create(
            organization_id=org_id,
            user_id=user_id,
            platform=platform,
            defaults={
                'is_active': True,
                'status': 'active',
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            }
        )
        return session

    @staticmethod
    def invalidate_session(session: BrowserSession):
        session.is_active = False
        session.status = 'expired'
        session.save(update_fields=['is_active', 'status'])
