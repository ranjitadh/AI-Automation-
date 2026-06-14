from .base import BasePlatformHandler

class IndeedHandler(BasePlatformHandler):
    def detect(self) -> bool:
        return 'indeed.com' in self.page.url.lower()

    def apply(self) -> tuple:
        self.log("Indeed Apply flow starting")

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

        for step in range(10):
            self.page.wait_for_timeout(2000)
            self._fill_fields()
            self._handle_questions()

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

        self.log("Indeed application flow completed")
        return True, self.logs, None

    def _fill_fields(self):
        for field in self.page.locator('input:visible, textarea:visible').all():
            try:
                name = (field.get_attribute('name') or '').lower()
                placeholder = (field.get_attribute('placeholder') or '').lower()
                ftype = field.get_attribute('type') or ''
                if ftype in ('submit', 'button', 'hidden', 'checkbox', 'radio', 'file'):
                    continue
                if field.input_value():
                    continue
                if 'email' in name or 'email' in placeholder:
                    field.fill(self.info.get('email', ''))
                elif 'phone' in name or 'tel' in name or 'phone' in placeholder:
                    field.fill(self.info.get('phone', ''))
                elif 'name' in name or 'name' in placeholder:
                    field.fill(self.info.get('name', ''))
                elif field.evaluate('el => el.tagName') == 'TEXTAREA' or 'message' in name or 'cover' in name:
                    field.fill(self.cover_letter.content if hasattr(self.cover_letter, 'content') else self.cover_letter or '')
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
