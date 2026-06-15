from .base import BasePlatformHandler


class WorkdayHandler(BasePlatformHandler):
    def detect(self) -> bool:
        url = self.page.url.lower()
        return 'myworkdayjobs.com' in url or 'workday' in url or 'wd5.myworkdayjobs.com' in url

    def apply(self) -> tuple:
        self.log("Workday ATS — applying via Workday form")

        if not self.handle_captcha():
            return False, self.logs, None

        apply_btn = self.page.locator(
            'button:has-text("Apply"), '
            'a:has-text("Apply"), '
            '[aria-label*="Apply"], '
            '[data-automation-id*="apply"]'
        ).first

        if apply_btn.count() and apply_btn.is_visible():
            apply_btn.click()
            self.page.wait_for_timeout(5000)
        else:
            self.log("Workday apply button not found", "warning")
            return False, self.logs, None

        self.page.wait_for_load_state('networkidle')
        screenshot_before = self.take_screenshot("workday_apply_start")

        for _ in range(20):
            self.page.wait_for_timeout(2000)
            self._fill_fields()
            self.upload_resume(self.info.get('resume_path'))
            self.answer_screening_questions()

            next_btn = self.page.locator(
                'button:has-text("Next"), '
                'button:has-text("Continue"), '
                '[data-automation-id*="next"], '
                '[data-automation-id*="continue"]'
            ).first

            if next_btn.count() == 0 or not next_btn.is_visible():
                break
            next_btn.click()
            self.page.wait_for_timeout(2000)

        submit_btn = self.page.locator(
            'button:has-text("Submit"), '
            '[data-automation-id*="submit"]'
        ).first

        if submit_btn.count() and submit_btn.is_visible():
            submit_btn.click()
            self.page.wait_for_timeout(5000)
            self.take_screenshot("workday_submitted")
            self.log("Workday application submitted")
            return True, self.logs, self.screenshots[-1] if self.screenshots else None

        self.verify_submission()
        self.take_screenshot("workday_result")
        self.log("Workday application flow completed")
        return True, self.logs, self.screenshots[-1] if self.screenshots else None

    def _fill_fields(self):
        for field in self.page.locator('input:visible, textarea:visible, select:visible').all():
            try:
                name = (field.get_attribute('name') or '').lower()
                placeholder = (field.get_attribute('placeholder') or '').lower()
                aria = (field.get_attribute('aria-label') or '').lower()
                ftype = field.get_attribute('type') or ''
                if ftype in ('submit', 'button', 'hidden', 'checkbox', 'radio', 'file'):
                    continue
                try:
                    if field.input_value():
                        continue
                except Exception:
                    continue
                combined = f"{name} {placeholder} {aria}"
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
                    elif 'first' in name or 'first' in placeholder:
                        field.fill(self.info.get('name', '').split()[0])
                    elif 'last' in name or 'last' in placeholder:
                        parts = self.info.get('name', '').split()
                        field.fill(parts[-1] if len(parts) > 1 else '')
            except Exception:
                continue
