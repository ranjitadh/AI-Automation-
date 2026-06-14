from urllib.parse import urlparse
from .base import BasePlatformHandler

class GenericHandler(BasePlatformHandler):
    def detect(self) -> bool:
        return True

    def apply(self) -> tuple:
        self.log("Generic career page form filler")

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

        self._fill_form()
        self._handle_submit()
        return True, self.logs, None

    def _fill_form(self):
        for field in self.page.locator('input:visible, textarea:visible, select:visible').all():
            try:
                tag = field.evaluate('el => el.tagName')
                name = (field.get_attribute('name') or '').lower()
                ftype = field.get_attribute('type') or ''
                placeholder = (field.get_attribute('placeholder') or '').lower()

                if ftype in ('submit', 'button', 'hidden'):
                    continue
                try:
                    if field.input_value():
                        continue
                except Exception:
                    continue

                content = self.cover_letter.content if hasattr(self.cover_letter, 'content') else str(self.cover_letter or '')

                if tag == 'TEXTAREA':
                    field.fill(content)
                elif tag == 'SELECT':
                    opts = field.locator('option').all()
                    if len(opts) > 0:
                        field.select_option(index=0)
                else:
                    if 'email' in name or 'email' in placeholder:
                        field.fill(self.info.get('email', ''))
                    elif 'phone' in name or 'tel' in name or 'phone' in placeholder:
                        field.fill(self.info.get('phone', ''))
                    elif 'name' in name or 'name' in placeholder:
                        field.fill(self.info.get('name', ''))
                    elif 'linkedin' in name:
                        field.fill(self.info.get('linkedin', ''))
                    elif 'website' in name or 'portfolio' in name:
                        field.fill(self.info.get('website', ''))
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
