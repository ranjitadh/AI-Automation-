from abc import ABC, abstractmethod
from typing import Optional

class BasePlatformHandler(ABC):
    def __init__(self, page, context, info, cover_letter):
        self.page = page
        self.context = context
        self.info = info
        self.cover_letter = cover_letter
        self.logs = []

    def log(self, msg, level='info'):
        self.logs.append(f"[{level.upper()}] {msg}")

    @abstractmethod
    def detect(self) -> bool:
        pass

    @abstractmethod
    def apply(self) -> tuple:
        pass

    def handle_captcha(self):
        """Override if platform-specific captcha handling needed"""
        return False

    def verify_submission(self) -> bool:
        """Check for success indicators on the page"""
        success_selectors = [
            'text=Application submitted',
            'text=Thank you for your application',
            'text=Your application has been received',
            '.application-success',
            '[data-testid="success-message"]',
            'text=We received your application',
        ]
        for selector in success_selectors:
            try:
                if self.page.locator(selector).count() > 0:
                    return True
            except Exception:
                continue
        return False
