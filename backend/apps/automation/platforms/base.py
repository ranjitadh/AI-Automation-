import os
import json
import uuid
import re
import logging
import tempfile
from abc import ABC, abstractmethod
from typing import Optional
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


class BasePlatformHandler(ABC):
    def __init__(self, page, context, info, cover_letter, answers=None):
        self.page = page
        self.context = context
        self.info = info
        self.cover_letter = cover_letter
        self.answers = answers or []
        self.logs = []
        self.screenshots = []

    def log(self, msg, level='info'):
        self.logs.append(f"[{level.upper()}] {msg}")

    @abstractmethod
    def detect(self) -> bool:
        pass

    @abstractmethod
    def apply(self) -> tuple:
        pass

    def handle_captcha(self) -> bool:
        if self._detect_captcha():
            self.log("CAPTCHA detected — blocking submission", "error")
            return False
        return True

    def _detect_captcha(self) -> bool:
        captcha_indicators = [
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]',
            'iframe[src*="turnstile"]',
            'div[class*="recaptcha"]',
            'div[class*="h-captcha"]',
            'div[class*="cf-turnstile"]',
            'input[name*="captcha"]',
            'input[id*="captcha"]',
            '[aria-label*="captcha"]',
            'img[alt*="captcha"]',
            '#captcha',
            '.captcha',
            '[data-sitekey]',
        ]
        for selector in captcha_indicators:
            try:
                if self.page.locator(selector).count() > 0:
                    return True
            except Exception:
                continue
        return False

    def verify_submission(self) -> bool:
        success_selectors = [
            'text=Application submitted',
            'text=Thank you for your application',
            'text=Your application has been received',
            'text=We received your application',
            'text=Application received',
            'text=Successfully applied',
            'text=Submitted successfully',
            '.application-success',
            '[data-testid="success-message"]',
            '[role="alert"][aria-live="polite"]',
            '.css-1i0v9q0',
            '[class*="success"]',
            '[class*="confirmation"]',
        ]
        for selector in success_selectors:
            try:
                if self.page.locator(selector).count() > 0:
                    self.log(f"Submission confirmed via: {selector}")
                    return True
            except Exception:
                continue
        return False

    def take_screenshot(self, name="application"):
        try:
            path = f"/tmp/{name}_{uuid.uuid4().hex[:8]}.png"
            self.page.screenshot(path=path)
            self.screenshots.append(path)
            self.log(f"Screenshot saved: {path}")
            return path
        except Exception as e:
            self.log(f"Screenshot failed: {e}", "warning")
            return None

    def upload_resume(self, resume_path: Optional[str] = None):
        if not resume_path:
            resume_path = self.info.get('resume_path')
        local_path = self._resolve_resume_path(resume_path)
        if not local_path or not os.path.exists(local_path):
            self.log("No resume file available for upload", "warning")
            return False
        try:
            file_inputs = self.page.locator('input[type="file"]').all()
            if not file_inputs:
                self.log("No file upload fields detected", "info")
                return False
            for fi in file_inputs:
                try:
                    fi.set_input_files(local_path)
                    self.log(f"Uploaded resume: {local_path}")
                except Exception as e:
                    self.log(f"File upload failed: {e}", "warning")
            return True
        except Exception as e:
            self.log(f"Resume upload error: {e}", "error")
            return False

    def _resolve_resume_path(self, resume_path: Optional[str]) -> Optional[str]:
        if not resume_path:
            return None
        if os.path.exists(resume_path):
            return resume_path
        try:
            if default_storage.exists(resume_path):
                suffix = os.path.splitext(resume_path)[1] or '.pdf'
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.write(default_storage.open(resume_path).read())
                tmp.close()
                self.log(f"Downloaded resume from storage: {tmp.name}")
                return tmp.name
        except Exception:
            pass
        try:
            if resume_path.startswith('http'):
                import httpx
                r = httpx.get(resume_path, timeout=15.0, follow_redirects=True)
                if r.status_code == 200:
                    suffix = '.pdf'
                    if 'content-type' in r.headers:
                        ct = r.headers['content-type']
                        suffix = '.pdf' if 'pdf' in ct else '.docx' if 'word' in ct else '.txt'
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                    tmp.write(r.content)
                    tmp.close()
                    self.log(f"Downloaded resume from URL: {tmp.name}")
                    return tmp.name
        except Exception:
            pass
        return None

    def answer_screening_questions(self):
        try:
            questions = self._extract_questions()
            if not questions:
                return False
            self.log(f"Found {len(questions)} screening questions to answer")
            for q in questions:
                self._answer_single_question(q)
            return True
        except Exception as e:
            self.log(f"Question answering error: {e}", "warning")
            return False

    def _extract_questions(self) -> list:
        questions = []
        seen = set()
        selectors = [
            '.application-question label',
            '.field-label',
            '[data-testid="question-label"]',
            'label:has(+ input:visible)',
            'label:has(+ textarea:visible)',
            'label:has(+ select:visible)',
            'p:has(+ textarea:visible)',
            'legend',
            '.label',
            'label:has(+ div > input)',
            'label:has(+ div > textarea)',
            'span[class*="label"]:has(+ input)',
            'div[class*="question"] label',
            'div[class*="field"] label',
        ]
        for selector in selectors:
            try:
                for el in self.page.locator(selector).all():
                    try:
                        text = el.text_content()
                        if text and len(text) > 5 and len(text) < 500:
                            normalized = text.strip().lower()
                            if normalized not in seen:
                                seen.add(normalized)
                                questions.append(text.strip())
                    except Exception:
                        continue
            except Exception:
                continue
        return questions

    def _answer_single_question(self, question_text: str):
        question_lower = question_text.lower()
        answer = self._find_matching_answer(question_lower)

        target = self._find_field_for_question(question_lower, answer)

        if target is None:
            self.log(f"No suitable field found for: {question_text[:50]}", "debug")
            return

        try:
            tag = target.evaluate('el => el.tagName')
            if tag == 'SELECT':
                opts = target.locator('option').all()
                for opt in opts:
                    opt_text = (opt.text_content() or '').lower()
                    if any(kw in opt_text for kw in ['yes', 'true', 'applicable', answer.lower()[:20]]):
                        opt.select_option(value=opt.get_attribute('value') or '')
                        break
                else:
                    if opts:
                        target.select_option(index=0)
            elif tag == 'TEXTAREA':
                text = answer if len(answer) > 10 else self.cover_letter or answer
                target.fill(text)
            else:
                ftype = target.get_attribute('type') or ''
                if ftype in ('checkbox', 'radio'):
                    is_yes = answer.lower() in ('yes', 'true', 'y')
                    if is_yes:
                        target.check()
                    else:
                        target.uncheck()
                elif ftype == 'file':
                    local_path = self._resolve_resume_path(answer)
                    if local_path:
                        target.set_input_files(local_path)
                else:
                    target.fill(answer)
        except Exception as e:
            self.log(f"Failed to fill field for '{question_text[:40]}': {e}", "debug")

    def _find_field_for_question(self, question_lower: str, answer: str):
        label_map = {}
        for label_el in self.page.locator('label').all():
            try:
                for_text = label_el.get_attribute('for')
                text = (label_el.text_content() or '').strip().lower()
                if for_text and text:
                    label_map[for_text] = text
            except Exception:
                continue

        for selector in ['input:visible', 'textarea:visible', 'select:visible']:
            for field in self.page.locator(selector).all():
                try:
                    if not field.is_visible():
                        continue
                    field_id = field.get_attribute('id') or ''
                    field_name = (field.get_attribute('name') or '').lower()
                    field_placeholder = (field.get_attribute('placeholder') or '').lower()
                    aria_label = (field.get_attribute('aria-label') or '').lower()

                    if field_id and field_id in label_map:
                        label_text = label_map[field_id]
                        if question_lower[:30] in label_text or label_text[:30] in question_lower:
                            return field

                    combined = f"{field_name} {field_placeholder} {aria_label}"
                    if question_lower[:20] in combined or combined[:20] in question_lower:
                        try:
                            val = field.input_value()
                            if val is None or val == '':
                                return field
                        except Exception:
                            return field
                except Exception:
                    continue

        for selector in ['input:visible', 'textarea:visible', 'select:visible']:
            for field in self.page.locator(selector).all():
                try:
                    if not field.is_visible():
                        continue
                    try:
                        val = field.input_value()
                        if val is None or val == '':
                            return field
                    except Exception:
                        return field
                except Exception:
                    continue

        return None

    def _find_matching_answer(self, question_lower: str) -> str:
        name = self.info.get('name', '')
        email = self.info.get('email', '')
        phone = self.info.get('phone', '')

        if 'name' in question_lower and ('full' in question_lower or 'your' in question_lower):
            return name
        if 'email' in question_lower:
            return email
        if 'phone' in question_lower or 'tel' in question_lower:
            return phone
        if 'linkedin' in question_lower:
            return self.info.get('linkedin', '')
        if 'website' in question_lower or 'portfolio' in question_lower:
            return self.info.get('website', '')
        if 'years' in question_lower and ('experience' in question_lower or 'python' in question_lower):
            return str(self.info.get('years_of_experience', '5+'))

        for ans in self.answers:
            q = ans.get('question', '').lower()
            if question_lower[:30] in q or q[:30] in question_lower:
                return ans.get('answer', '')

        if 'why' in question_lower and ('company' in question_lower or 'work' in question_lower):
            return f"I am excited about this opportunity because my background in {self.info.get('skills', 'this field')} aligns well with the role requirements."
        if 'authoriz' in question_lower or 'visa' in question_lower or 'sponsor' in question_lower:
            return self.info.get('work_authorization', 'Yes, I am authorized to work')
        if 'salary' in question_lower:
            return self.info.get('salary_expectation', 'Open to discussion based on total compensation')
        if 'start' in question_lower or 'available' in question_lower or 'notice' in question_lower:
            return self.info.get('availability', 'Immediately')
        if 'degree' in question_lower or 'education' in question_lower or 'qualification' in question_lower:
            return self.info.get('highest_education', "Bachelor's degree")
        if 'gender' in question_lower or 'race' in question_lower or 'ethnicity' in question_lower or 'veteran' in question_lower or 'disability' in question_lower:
            return "Prefer not to say"
        if 'referral' in question_lower or 'source' in question_lower or 'hear' in question_lower:
            return "LinkedIn"

        return "I have relevant experience that aligns well with this role."
