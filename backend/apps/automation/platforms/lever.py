from .base import BasePlatformHandler


class LeverHandler(BasePlatformHandler):
    def detect(self) -> bool:
        url = self.page.url.lower()
        return 'lever.co' in url or 'jobs.lever.co' in url

    def apply(self) -> tuple:
        self.log("Lever ATS — applying via embedded form")

        if not self.handle_captcha():
            return False, self.logs, None

        try:
            iframes = self.page.locator('iframe[src*="lever"]').all()
            for iframe in iframes:
                try:
                    frame = iframe.content_frame()
                    if frame:
                        apply_btn = frame.locator('a:has-text("Apply"), button:has-text("Apply")').first
                        if apply_btn.count():
                            apply_btn.click()
                            self.page.wait_for_timeout(3000)
                            break
                except Exception:
                    continue
        except Exception:
            pass

        self.page.wait_for_timeout(2000)
        screenshot_before = self.take_screenshot("lever_apply_start")

        for _ in range(15):
            self.page.wait_for_timeout(1500)
            self._fill_fields()
            self.upload_resume(self.info.get('resume_path'))
            self.answer_screening_questions()

            next_btn = self.page.locator(
                'button:has-text("Next"), '
                'button:has-text("Continue"), '
                'input[type="submit"]'
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
            self.take_screenshot("lever_submitted")
            self.log("Lever application submitted")
            return True, self.logs, self.screenshots[-1] if self.screenshots else None

        self.verify_submission()
        self.take_screenshot("lever_result")
        self.log("Lever application flow completed")
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
                    if 'email' in combined or field.get_attribute('type') == 'email':
                        field.fill(self.info.get('email', ''))
                    elif 'phone' in combined or 'tel' in combined:
                        field.fill(self.info.get('phone', ''))
                    elif 'name' in combined:
                        field.fill(self.info.get('name', ''))
                    elif 'linkedin' in combined:
                        field.fill(self.info.get('linkedin', ''))
            except Exception:
                continue
