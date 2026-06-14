import uuid
from pathlib import Path
from urllib.parse import urlparse
from django.conf import settings
from playwright.sync_api import sync_playwright

MEDIA = Path(settings.MEDIA_ROOT) / 'application_screenshots'

def ss(page, name):
    MEDIA.mkdir(parents=True, exist_ok=True)
    p = MEDIA / name
    page.screenshot(path=str(p))
    return f"application_screenshots/{name}"

def fill_field(field, value):
    if field.is_visible() and field.get_attribute("type") not in ("submit", "button", "hidden", "checkbox", "radio"):
        field.fill(value)

def _fill_common(page, info, cover):
    for f in page.locator("input:visible, textarea:visible").all():
        c = ((f.get_attribute("name") or "") + " " + (f.get_attribute("id") or "") + " " + (f.get_attribute("placeholder") or "")).lower()
        if f.input_value(): continue
        if "email" in c or f.get_attribute("type") == "email": fill_field(f, info['email'])
        elif "phone" in c or "tel" in c: fill_field(f, info['phone'])
        elif "name" in c: fill_field(f, info['name'])
        elif f.evaluate("el => el.tagName") == "TEXTAREA" or "message" in c or "cover" in c: fill_field(f, cover)

def run_auto_apply_model(job, cover_letter, applicant_info=None):
    logs, url = [], job.application_page_url or job.job_description_url or ""
    if not url: return False, logs + ["[Error] No URL"], None
    info = applicant_info or {'name': 'Your Name', 'email': 'your@email.com', 'phone': '+1-234-567-8900'}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36", viewport={"width": 1280, "height": 800})
            page = ctx.new_page()
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            logs.append(f"[OK] Loaded {url}")

            url_l = page.url.lower()
            if "linkedin.com" in url_l and ("easyapply" in url_l or "jobs" in url_l):
                return _linkedin(page, logs, info, cover_letter)
            if "indeed.com" in url_l:
                return _indeed(page, logs, info, cover_letter)
            return _generic(page, logs, info, cover_letter)
    except Exception as e:
        logs.append(f"[Error] {e}")
        return False, logs, None

def _linkedin(page, logs, info, cover):
    logs.append("[LinkedIn] Easy Apply flow")
    btn = page.locator("button:has-text('Easy Apply'), button[aria-label*='Easy Apply']").first
    if btn.count(): btn.click(); page.wait_for_timeout(2000)
    else: return _generic(page, logs, info, cover)

    for _ in range(10):
        page.wait_for_timeout(1000)
        for ta in page.locator("textarea").all():
            if ta.is_visible() and len(ta.input_value()) < 10: ta.fill(cover); break
        _fill_common(page, info, cover)
        nxt = page.locator("button:has-text('Next'), button:has-text('Review'), button:has-text('Submit')").first
        if nxt.count() and nxt.is_visible(): nxt.click()
        else: break
        page.wait_for_timeout(1500)

    logs.append("[LinkedIn] Done")
    browser = page.context.browser; browser.close()
    return True, logs, None

def _indeed(page, logs, info, cover):
    logs.append("[Indeed] Apply flow")
    btn = page.locator("button:has-text('Apply now'), a:has-text('Apply Now')").first
    if btn.count(): btn.click(); page.wait_for_timeout(3000)
    else: return _generic(page, logs, info, cover)
    page.wait_for_timeout(2000); _fill_common(page, info, cover)
    for _ in range(5):
        nxt = page.locator("button:has-text('Continue'), button:has-text('Submit')").first
        if nxt.count() and nxt.is_visible(): nxt.click(); page.wait_for_timeout(2000)
        else: break
    logs.append("[Indeed] Done")
    browser = page.context.browser; browser.close()
    return True, logs, None

def _generic(page, logs, info, cover):
    logs.append("[Generic] Form fill")
    for kw in ["apply", "career", "careers", "job", "jobs", "application"]:
        for link in page.locator("a").all():
            href = link.get_attribute("href") or ""
            if kw in href.lower() or kw in (link.text_content() or "").lower():
                if not href.startswith("http"):
                    p = urlparse(page.url)
                    href = f"{p.scheme}://{p.netloc}{href}" if href.startswith("/") else f"{page.url.rstrip('/')}/{href}"
                page.goto(href, timeout=20000, wait_until="domcontentloaded")
                break
        else: continue
        break

    if page.locator("form").count() == 0:
        logs.append("[Failed] No form found")
        browser = page.context.browser; browser.close()
        return False, logs, None

    _fill_common(page, info, cover)
    sub = page.locator("button[type='submit'], input[type='submit']").first
    if sub.count() == 0:
        for b in page.locator("button").all():
            if "submit" in (b.text_content() or "").lower() or "apply" in (b.text_content() or "").lower(): sub = b; break
    if sub.count(): sub.click(); page.wait_for_timeout(3000)
    logs.append("[Generic] Submitted")
    browser = page.context.browser; browser.close()
    return True, logs, None
