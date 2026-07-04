from .base import BasePlatformHandler


class IndeedHandler(BasePlatformHandler):
    def detect(self) -> bool:
        return 'indeed.com' in self.page.url.lower()

    def apply(self) -> tuple:
        self.log("Indeed Apply flow starting")

        if not self.handle_captcha():
            return False, self.logs, None

        apply_btn = self.page.locator(
            'button:has-text("Apply now"), '
            'a:has-text("Apply Now"), '
            '[data-testid="applyNow"]'
        ).first

        if apply_btn.count() == 0 or not apply_btn.is_visible():
            self.log("No Apply Now button found", "warning")
            return False, self.logs, None

        apply_btn.click()
        self.page.wait_for_timeout(5000)
        screenshot_before = self.take_screenshot("indeed_apply_start")

        for step in range(10):
            self.page.wait_for_timeout(2000)
            self._fill_fields()
            self._handle_questions()
            self.upload_resume(self.info.get('resume_path'))
            self.answer_screening_questions()

            if self._detect_captcha():
                self.log("CAPTCHA detected during Indeed flow", "error")
                return False, self.logs, screenshot_before

            nxt = self.page.locator(
                'button:has-text("Continue"), '
                'button:has-text("Next"), '
                'button:has-text("Submit"), '
                'button:has-text("Submit application")'
            ).first

            if nxt.count() == 0 or not nxt.is_visible():
                break
            nxt.click()
            self.page.wait_for_timeout(2000)

        self.verify_submission()
        self.take_screenshot("indeed_result")
        self.log("Indeed application flow completed")
        return True, self.logs, self.screenshots[-1] if self.screenshots else None

    def _fill_fields(self):
        for field in self.page.locator('input:visible, textarea:visible').all():
            try:
                name = (field.get_attribute('name') or '').lower()
                placeholder = (field.get_attribute('placeholder') or '').lower()
                aria_label = (field.get_attribute('aria-label') or '').lower()
                ftype = field.get_attribute('type') or ''
                if ftype in ('submit', 'button', 'hidden', 'checkbox', 'radio', 'file'):
                    continue
                if field.input_value():
                    continue
                combined = f"{name} {placeholder} {aria_label}"
                if 'email' in combined or field.get_attribute('type') == 'email':
                    field.fill(self.info.get('email', ''))
                elif 'phone' in combined or 'tel' in combined:
                    field.fill(self.info.get('phone', ''))
                elif 'name' in combined:
                    field.fill(self.info.get('name', ''))
                elif field.evaluate('el => el.tagName') == 'TEXTAREA' or 'message' in combined or 'cover' in combined:
                    cover = self.cover_letter
                    if hasattr(cover, 'content'):
                        cover = cover.content
                    field.fill(cover or '')
            except Exception:
                continue

    def _handle_questions(self):
        for select in self.page.locator('select:visible').all():
            try:
                opts = select.locator('option').all()
                if len(opts) > 0:
                    select.select_option(index=0)
            except Exception:
                continue
