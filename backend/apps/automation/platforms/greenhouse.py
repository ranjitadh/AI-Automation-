from .base import BasePlatformHandler


class GreenhouseHandler(BasePlatformHandler):
    def detect(self) -> bool:
        url = self.page.url.lower()
        return 'greenhouse.io' in url or 'greenhouse' in url

    def apply(self) -> tuple:
        self.log("Greenhouse Apply flow")

        if not self.handle_captcha():
            return False, self.logs, None

        apply_btn = self.page.locator(
            'a:has-text("Apply"), '
            'button:has-text("Apply"), '
            '[data-action="apply"]'
        ).first

        if apply_btn.count() and apply_btn.is_visible():
            apply_btn.click()
            self.page.wait_for_timeout(3000)

        self.page.wait_for_load_state('networkidle')
        screenshot_before = self.take_screenshot("greenhouse_apply_start")

        for _ in range(15):
            self.page.wait_for_timeout(1500)
            self._fill_fields()
            self._fill_textareas()
            self.upload_resume(self.info.get('resume_path'))
            self.answer_screening_questions()

            if self._detect_captcha():
                self.log("CAPTCHA detected during Greenhouse flow", "error")
                return False, self.logs, screenshot_before

            next_btn = self.page.locator(
                'button:has-text("Next"), '
                'button:has-text("Review"), '
                'input[type="submit"]'
            ).first

            if next_btn.count() == 0:
                break
            next_btn.click()
            self.page.wait_for_timeout(2000)

        submit_btn = self.page.locator(
            'button:has-text("Submit"), '
            'input[type="submit"]'
        ).first

        if submit_btn.count() and submit_btn.is_visible():
            submit_btn.click()
            self.page.wait_for_timeout(3000)
            self.take_screenshot("greenhouse_submitted")
            self.log("Greenhouse application submitted")
            return True, self.logs, self.screenshots[-1] if self.screenshots else None

        self.log("Could not complete Greenhouse application", "error")
        return False, self.logs, screenshot_before

    def _fill_fields(self):
        for inp in self.page.locator('input:visible:not([type="hidden"]):not([type="submit"])').all():
            try:
                name = (inp.get_attribute('name') or '').lower()
                aria_label = (inp.get_attribute('aria-label') or '').lower()
                placeholder = (inp.get_attribute('placeholder') or '').lower()
                ftype = inp.get_attribute('type') or ''
                if ftype in ('checkbox', 'radio', 'file'):
                    continue
                if inp.input_value():
                    continue
                combined = f"{name} {placeholder} {aria_label}"
                if 'email' in combined:
                    inp.fill(self.info.get('email', ''))
                elif 'phone' in combined:
                    inp.fill(self.info.get('phone', ''))
                elif 'first_name' in name or 'first' in name:
                    inp.fill(self.info.get('name', '').split()[0])
                elif 'last_name' in name or 'last' in name:
                    parts = self.info.get('name', '').split()
                    inp.fill(parts[-1] if len(parts) > 1 else '')
                elif 'linkedin' in combined:
                    inp.fill(self.info.get('linkedin', ''))
            except Exception:
                continue

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
