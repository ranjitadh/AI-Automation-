from .base import BasePlatformHandler


class BambooHRHandler(BasePlatformHandler):
    def detect(self) -> bool:
        url = self.page.url.lower()
        return 'bamboohr.com' in url or 'bamboo' in url

    def apply(self) -> tuple:
        self.log("BambooHR ATS — applying")

        if not self.handle_captcha():
            return False, self.logs, None

        apply_btn = self.page.locator(
            'a:has-text("Apply"), '
            'button:has-text("Apply"), '
            '[class*="apply"] a'
        ).first

        if apply_btn.count() and apply_btn.is_visible():
            apply_btn.click()
            self.page.wait_for_timeout(3000)

        self.page.wait_for_load_state('networkidle')
        screenshot_before = self.take_screenshot("bamboohr_apply_start")

        for _ in range(15):
            self.page.wait_for_timeout(1500)
            self._fill_fields()
            self.upload_resume(self.info.get('resume_path'))
            self.answer_screening_questions()

            next_btn = self.page.locator(
                'button:has-text("Next"), '
                'button:has-text("Continue")'
            ).first

            if next_btn.count() == 0 or not next_btn.is_visible():
                break
            next_btn.click()
            self.page.wait_for_timeout(1500)

        submit_btn = self.page.locator(
            'button:has-text("Submit"), '
            'button[type="submit"]'
        ).first

        if submit_btn.count() and submit_btn.is_visible():
            submit_btn.click()
            self.page.wait_for_timeout(3000)
            self.take_screenshot("bamboohr_submitted")
            self.log("BambooHR application submitted")
            return True, self.logs, self.screenshots[-1] if self.screenshots else None

        self.verify_submission()
        self.take_screenshot("bamboohr_result")
        self.log("BambooHR flow completed")
        return True, self.logs, self.screenshots[-1] if self.screenshots else None

    def _fill_fields(self):
        for field in self.page.locator('input:visible, textarea:visible, select:visible').all():
            try:
                name = (field.get_attribute('name') or '').lower()
                placeholder = (field.get_attribute('placeholder') or '').lower()
                ftype = field.get_attribute('type') or ''
                if ftype in ('submit', 'button', 'hidden', 'checkbox', 'radio', 'file'):
                    continue
                if field.input_value():
                    continue
                combined = f"{name} {placeholder}"
                tag = field.evaluate('el => el.tagName')
                if tag == 'TEXTAREA':
                    cover = self.cover_letter
                    if hasattr(cover, 'content'):
                        cover = cover.content
                    field.fill(cover or '')
                elif tag == 'SELECT':
                    opts = field.locator('option').all()
                    if len(opts) > 0:
                        field.select_option(index=0)
                else:
                    if 'email' in combined:
                        field.fill(self.info.get('email', ''))
                    elif 'phone' in combined or 'tel' in combined:
                        field.fill(self.info.get('phone', ''))
                    elif 'name' in combined:
                        field.fill(self.info.get('name', ''))
            except Exception:
                continue
