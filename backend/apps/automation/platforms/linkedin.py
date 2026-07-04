from .base import BasePlatformHandler


class LinkedInHandler(BasePlatformHandler):
    def detect(self) -> bool:
        url = self.page.url.lower()
        return 'linkedin.com' in url

    def apply(self) -> tuple:
        self.log("LinkedIn Easy Apply flow starting")

        if not self.handle_captcha():
            return False, self.logs, None

        easy_apply_btn = self.page.locator(
            'button:has-text("Easy Apply"), '
            'button[aria-label*="Easy Apply"], '
            '.jobs-apply-button'
        ).first

        if easy_apply_btn.count() == 0 or not easy_apply_btn.is_visible():
            self.log("No Easy Apply button found", "warning")
            return False, self.logs, None

        easy_apply_btn.click()
        self.page.wait_for_timeout(3000)
        screenshot_before = self.take_screenshot("linkedin_apply_start")

        for step in range(15):
            self.page.wait_for_timeout(1500)

            self._fill_textareas()
            self._fill_inputs()
            self.upload_resume(self.info.get('resume_path'))
            self._handle_multichoice()
            self.answer_screening_questions()

            next_btn = self.page.locator(
                'button:has-text("Next"), '
                'button:has-text("Review"), '
                'button:has-text("Submit application"), '
                'button[aria-label*="Next"]'
            ).first

            if next_btn.count() == 0 or not next_btn.is_visible():
                self.log("No next button found, may be on final step", "info")
                break

            next_btn.click()
            self.page.wait_for_timeout(2000)

        submit_btn = self.page.locator(
            'button:has-text("Submit"), '
            'button:has-text("Submit application"), '
            'button[type="submit"]'
        ).first

        if submit_btn.count() and submit_btn.is_visible():
            submit_btn.click()
            self.page.wait_for_timeout(3000)
            self.take_screenshot("linkedin_submitted")
            self.log("Application submitted on LinkedIn")
            return True, self.logs, self.screenshots[-1] if self.screenshots else None

        self.log("Could not find submit button", "error")
        return False, self.logs, screenshot_before

    def _fill_textareas(self):
        for ta in self.page.locator('textarea:visible').all():
            try:
                if ta.is_visible() and len(ta.input_value() or '') < 10:
                    cover = self.cover_letter
                    if hasattr(cover, 'content'):
                        cover = cover.content
                    ta.fill(cover or '')
            except Exception:
                continue

    def _fill_inputs(self):
        for inp in self.page.locator('input:visible:not([type="hidden"]):not([type="submit"])').all():
            try:
                name = (inp.get_attribute('name') or '').lower()
                placeholder = (inp.get_attribute('placeholder') or '').lower()
                aria_label = (inp.get_attribute('aria-label') or '').lower()
                if inp.input_value():
                    continue
                combined = f"{name} {placeholder} {aria_label}"
                if 'email' in combined or inp.get_attribute('type') == 'email':
                    inp.fill(self.info.get('email', ''))
                elif 'phone' in combined or 'tel' in combined:
                    inp.fill(self.info.get('phone', ''))
                elif 'name' in combined:
                    inp.fill(self.info.get('name', ''))
            except Exception:
                continue

    def _handle_multichoice(self):
        for select in self.page.locator('select:visible').all():
            try:
                options = select.locator('option').all()
                if len(options) > 0:
                    select.select_option(index=0)
            except Exception:
                continue
