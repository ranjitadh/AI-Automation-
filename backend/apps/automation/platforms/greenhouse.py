from .base import BasePlatformHandler

class GreenhouseHandler(BasePlatformHandler):
    def detect(self) -> bool:
        url = self.page.url.lower()
        return 'greenhouse.io' in url or 'greenhouse' in url

    def apply(self) -> tuple:
        self.log("Greenhouse Apply flow")

        apply_btn = self.page.locator(
            'a:has-text("Apply"), '
            'button:has-text("Apply"), '
            '[data-action="apply"]'
        ).first

        if apply_btn.count() and apply_btn.is_visible():
            apply_btn.click()
            self.page.wait_for_timeout(3000)

        self.page.wait_for_load_state('networkidle')

        for _ in range(15):
            self.page.wait_for_timeout(1500)
            self._fill_fields()
            self._fill_textareas()
            self._handle_uploads()

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
            self.log("Greenhouse application submitted")
            return True, self.logs, None

        self.log("Could not complete Greenhouse application", "error")
        return False, self.logs, None

    def _fill_fields(self):
        for inp in self.page.locator('input:visible:not([type="hidden"]):not([type="submit"])').all():
            try:
                name = (inp.get_attribute('name') or '').lower()
                ftype = inp.get_attribute('type') or ''
                if ftype in ('checkbox', 'radio', 'file'):
                    continue
                if inp.input_value():
                    continue
                if 'email' in name:
                    inp.fill(self.info.get('email', ''))
                elif 'phone' in name:
                    inp.fill(self.info.get('phone', ''))
                elif 'first_name' in name or 'first' in name:
                    inp.fill(self.info.get('name', '').split()[0])
                elif 'last_name' in name or 'last' in name:
                    parts = self.info.get('name', '').split()
                    inp.fill(parts[-1] if len(parts) > 1 else '')
                elif 'linkedin' in name:
                    inp.fill(self.info.get('linkedin', ''))
            except Exception:
                continue

    def _fill_textareas(self):
        for ta in self.page.locator('textarea:visible').all():
            try:
                if ta.is_visible() and len(ta.input_value() or '') < 10:
                    ta.fill(self.cover_letter.content if hasattr(self.cover_letter, 'content') else self.cover_letter or '')
            except Exception:
                continue

    def _handle_uploads(self):
        for fi in self.page.locator('input[type="file"]:visible').all():
            try:
                self.log("Resume upload field detected", "info")
            except Exception:
                continue
