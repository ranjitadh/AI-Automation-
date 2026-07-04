from urllib.parse import urlparse
from .base import BasePlatformHandler


class GenericHandler(BasePlatformHandler):
    def detect(self) -> bool:
        return True

    def apply(self) -> tuple:
        self.log("Generic career page form filler")

        if not self.handle_captcha():
            return False, self.logs, None

        apply_keywords = ['apply', 'career', 'careers', 'job', 'jobs', 'application', 'positions', 'openings']
        for kw in apply_keywords:
            for link in self.page.locator('a').all():
                try:
                    href = link.get_attribute('href') or ''
                    text = link.text_content() or ''
                    if kw in href.lower() or kw in text.lower():
                        if not href.startswith('http'):
                            p = urlparse(self.page.url)
                            href = f"{p.scheme}://{p.netloc}{href}" if href.startswith('/') else f"{self.page.url.rstrip('/')}/{href}"
                        self.page.goto(href, timeout=20000, wait_until='domcontentloaded')
                        self.log(f"Navigated to {href}")
                        break
                except Exception:
                    continue
            else:
                continue
            break

        if self.page.locator('form').count() == 0:
            self.log("No form found on page", "error")
            return False, self.logs, None

        screenshot_before = self.take_screenshot("generic_form_start")
        self.upload_resume(self.info.get('resume_path'))
        self.answer_screening_questions()
        self._fill_form()

        if self._detect_captcha():
            self.log("CAPTCHA detected on form page", "error")
            return False, self.logs, screenshot_before

        self._handle_submit()
        self.take_screenshot("generic_result")
        return True, self.logs, self.screenshots[-1] if self.screenshots else screenshot_before

    def _fill_form(self):
        for field in self.page.locator('input:visible, textarea:visible, select:visible').all():
            try:
                tag = field.evaluate('el => el.tagName')
                name = (field.get_attribute('name') or '').lower()
                ftype = field.get_attribute('type') or ''
                placeholder = (field.get_attribute('placeholder') or '').lower()
                aria_label = (field.get_attribute('aria-label') or '').lower()

                if ftype in ('submit', 'button', 'hidden'):
                    continue
                try:
                    if field.input_value():
                        continue
                except Exception:
                    continue

                content = self.cover_letter
                if hasattr(content, 'content'):
                    content = content.content
                content = str(content or '')

                combined = f"{name} {placeholder} {aria_label}"

                if tag == 'TEXTAREA':
                    field.fill(content)
                elif tag == 'SELECT':
                    opts = field.locator('option').all()
                    if len(opts) > 0:
                        field.select_option(index=0)
                else:
                    if 'email' in combined or field.get_attribute('type') == 'email':
                        field.fill(self.info.get('email', ''))
                    elif 'phone' in combined or 'tel' in combined:
                        field.fill(self.info.get('phone', ''))
                    elif 'name' in combined:
                        field.fill(self.info.get('name', ''))
                    elif 'linkedin' in combined:
                        field.fill(self.info.get('linkedin', ''))
                    elif 'website' in combined or 'portfolio' in combined:
                        field.fill(self.info.get('website', ''))
                    elif 'resume' in name or 'cv' in name or 'file' in ftype:
                        rp = self.info.get('resume_path')
                        if rp:
                            try:
                                local_path = self._resolve_resume_path(rp)
                                if local_path:
                                    field.set_input_files(local_path)
                            except Exception:
                                pass
            except Exception:
                continue

    def _handle_submit(self):
        submit_btn = self.page.locator(
            'button[type="submit"], '
            'input[type="submit"], '
            'button:has-text("Submit"), '
            'button:has-text("Apply"), '
            'button:has-text("Send")'
        ).first

        if submit_btn.count() and submit_btn.is_visible():
            submit_btn.click()
            self.page.wait_for_timeout(3000)
            self.log("Form submitted")
        else:
            self.log("No submit button found", "warning")
