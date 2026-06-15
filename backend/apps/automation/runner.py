import logging
import time
import tempfile
from typing import Optional, Tuple
from playwright.sync_api import sync_playwright
from apps.automation.anti_detection import AntiDetectionManager
from apps.automation.platforms.linkedin import LinkedInHandler
from apps.automation.platforms.indeed import IndeedHandler
from apps.automation.platforms.greenhouse import GreenhouseHandler
from apps.automation.platforms.lever import LeverHandler
from apps.automation.platforms.ashby import AshbyHandler
from apps.automation.platforms.workday import WorkdayHandler
from apps.automation.platforms.smartrecruiters import SmartRecruitersHandler
from apps.automation.platforms.bamboohr import BambooHRHandler
from apps.automation.platforms.generic import GenericHandler

logger = logging.getLogger(__name__)

PLATFORM_HANDLERS = [
    LinkedInHandler,
    IndeedHandler,
    GreenhouseHandler,
    LeverHandler,
    AshbyHandler,
    WorkdayHandler,
    SmartRecruitersHandler,
    BambooHRHandler,
    GenericHandler,
]

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5


def detect_platform(job) -> str:
    url = (job.application_page_url or job.apply_url or job.direct_apply_url or '').lower()
    platform = (job.platform or '').lower()

    if platform:
        return platform
    if 'linkedin.com' in url:
        return 'linkedin'
    if 'indeed.com' in url:
        return 'indeed'
    if 'greenhouse.io' in url:
        return 'greenhouse'
    if 'lever.co' in url:
        return 'lever'
    if 'ashbyhq.com' in url:
        return 'ashby'
    if 'myworkdayjobs.com' in url or 'workday' in url:
        return 'workday'
    if 'smartrecruiters.com' in url:
        return 'smartrecruiters'
    if 'bamboohr.com' in url:
        return 'bamboohr'
    return 'generic'


def run_automation(job, cover_letter, applicant_info=None) -> Tuple[bool, list, Optional[str]]:
    logs = []
    url = job.application_page_url or job.apply_url or job.direct_apply_url or ''
    if not url:
        logs.append("[ERROR] No application URL found")
        return False, logs, None

    info = applicant_info or {
        'name': 'Applicant Name',
        'email': 'applicant@email.com',
        'phone': '+1-234-567-8900',
        'linkedin': '',
        'website': '',
        'resume_path': None,
    }

    answers = info.pop('answers', [])

    anti_detect = AntiDetectionManager()

    last_error = None
    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            logs.append(f"[RETRY] Attempt {attempt + 1}/{MAX_RETRIES} after {RETRY_DELAY_SECONDS}s")
            time.sleep(RETRY_DELAY_SECONDS)

        browser = None
        try:
            with sync_playwright() as p:
                browser_args = {
                    'headless': True,
                    'args': [
                        '--no-sandbox',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--disable-features=IsolateOrigins,site-per-process',
                    ]
                }

                browser = p.chromium.launch(**browser_args)
                context_args = anti_detect.get_browser_context_args()
                context = browser.new_context(**context_args)
                context.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )

                page = context.new_page()
                page.set_default_timeout(60000)

                page.on('console', lambda msg: logs.append(f"[CONSOLE] {msg.type}: {msg.text}"))
                page.on('requestfailed',
                        lambda req: logs.append(
                            f"[REQUEST_FAILED] {req.url} ({req.failure.error_text if req.failure else 'unknown'})"))
                page.on('pageerror', lambda err: logs.append(f"[PAGE_ERROR] {err}"))

                anti_detect.random_mouse_movement(page)

                logs.append(f"[INFO] Navigating to {url}")
                page.goto(url, timeout=60000, wait_until='domcontentloaded')
                anti_detect.random_scroll(page)
                anti_detect.human_delay(1000, 3000)

                handler_class = GenericHandler
                detected_platform = detect_platform(job)

                for handler_cls in PLATFORM_HANDLERS:
                    handler = handler_cls(page, context, info, cover_letter, answers)
                    if handler.detect():
                        handler_class = handler_cls
                        logs.append(f"[INFO] Detected platform: {handler_cls.__name__}")
                        break
                else:
                    logs.append("[INFO] Using generic form filler")

                handler = handler_class(page, context, info, cover_letter, answers)
                success, handler_logs, screenshot_path = handler.apply()
                logs.extend(handler_logs)

                info['answers'] = answers

                if success:
                    return success, logs, screenshot_path
                else:
                    last_error = logs[-1] if logs else "Unknown error"
                    logs.append(f"[WARN] Attempt {attempt + 1} failed, will retry")

        except Exception as e:
            last_error = str(e)
            logs.append(f"[ERROR] Attempt {attempt + 1} failed: {str(e)}")
            logger.error(f"Playwright automation attempt {attempt + 1} failed: {e}", exc_info=True)
        finally:
            if browser:
                try:
                    browser.close()
                    logger.info("Browser closed successfully after automation attempt")
                except Exception as e:
                    logger.error(f"Failed to close browser: {e}")

    logs.append(f"[FAILED] All {MAX_RETRIES} attempts failed. Last error: {last_error}")
    return False, logs, None
