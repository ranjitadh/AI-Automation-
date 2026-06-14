from .base import BasePlatformHandler

class LinkedInHandler(BasePlatformHandler):
    def detect(self) -> bool:
        url = self.page.url.lower()
        return 'linkedin.com' in url

    def apply(self) -> tuple:
        self.log("LinkedIn Easy Apply flow starting")

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

        for step in range(15):
            self.page.wait_for_timeout(1500)

            self._fill_textareas()
            self._fill_inputs()
            self._handle_uploads()
            self._handle_multichoice()

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
            self.log("Application submitted on LinkedIn")
            return True, self.logs, None

        self.log("Could not find submit button", "error")
        return False, self.logs, None

    def _fill_textareas(self):
        for ta in self.page.locator('textarea:visible').all():
            try:
                if ta.is_visible() and len(ta.input_value() or '') < 10:
                    ta.fill(self.cover_letter.content if hasattr(self.cover_letter, 'content') else self.cover_letter or '')
            except Exception:
                continue

    def _fill_inputs(self):
        for inp in self.page.locator('input:visible:not([type="hidden"]):not([type="submit"])').all():
            try:
                name = (inp.get_attribute('name') or '').lower()
                placeholder = (inp.get_attribute('placeholder') or '').lower()
                if 'email' in name or 'email' in placeholder:
                    inp.fill(self.info.get('email', ''))
                elif 'phone' in name or 'phone' in placeholder or 'tel' in name:
                    inp.fill(self.info.get('phone', ''))
                elif 'name' in name or 'name' in placeholder:
                    inp.fill(self.info.get('name', ''))
            except Exception:
                continue

    def _handle_uploads(self):
        for file_input in self.page.locator('input[type="file"]:visible').all():
            try:
                self.log("File upload field detected (skipping automated upload)", "info")
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
