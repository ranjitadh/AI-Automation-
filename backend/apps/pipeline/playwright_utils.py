import os
import uuid
from pathlib import Path
from django.conf import settings
from playwright.sync_api import sync_playwright

def run_auto_apply_model(website_url, subject, body, agency_info=None):
    """
    Automates browsing a website to find a contact form, fills it, 
    submits it, and returns the screenshot path and execution logs.
    """
    logs = []
    screenshot_filename = None
    
    if not agency_info:
        agency_info = {
            'name': getattr(settings, 'AGENCY_NAME', 'Your Agency'),
            'email': getattr(settings, 'AGENCY_EMAIL', 'hello@youragency.com'),
            'phone': getattr(settings, 'AGENCY_PHONE', '+1-234-567-8900'),
        }

    logs.append(f"[System] Initializing Auto-Apply Model for: {website_url}")
    
    # Ensure media directory exists
    media_dir = Path(settings.MEDIA_ROOT) / 'outreach_screenshots'
    media_dir.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as p:
            logs.append("[1/4] Launching headless browser...")
            browser = p.chromium.launch(headless=True)
            
            # Use specific viewport and user agent to avoid bot detection
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            
            logs.append(f"[2/4] Navigating to {website_url}...")
            try:
                page.goto(website_url, timeout=30000, wait_until="domcontentloaded")
            except Exception as e:
                logs.append(f"[Error] Failed to load home page: {str(e)}. Attempting to prepend http/https if missing.")
                if not website_url.startswith(('http://', 'https://')):
                    website_url = 'https://' + website_url
                    page.goto(website_url, timeout=30000, wait_until="domcontentloaded")
                else:
                    raise e
            
            logs.append("[3/4] Searching for contact page or forms...")
            
            # Check if there's a form on the landing page first
            form = page.locator("form").first
            contact_page_url = website_url
            
            if form.count() == 0:
                logs.append("No form found on homepage. Scanning for contact or booking links...")
                
                # Look for common contact links
                contact_keywords = ["contact", "contact-us", "contactus", "about", "book", "write", "support", "get-in-touch", "inquiry"]
                links = page.locator("a")
                contact_link = None
                
                for i in range(links.count()):
                    link = links.nth(i)
                    href = link.get_attribute("href") or ""
                    text = (link.text_content() or "").lower().strip()
                    
                    if any(keyword in href.lower() or keyword in text for keyword in contact_keywords):
                        contact_link = href
                        logs.append(f"Discovered contact link candidate: {text} -> {href}")
                        break
                
                if contact_link:
                    # Resolve relative URL
                    if not contact_link.startswith(('http://', 'https://')):
                        if contact_link.startswith('/'):
                            from urllib.parse import urlparse
                            parsed_url = urlparse(website_url)
                            contact_page_url = f"{parsed_url.scheme}://{parsed_url.netloc}{contact_link}"
                        else:
                            contact_page_url = f"{website_url.rstrip('/')}/{contact_link}"
                            
                    logs.append(f"Navigating to contact page: {contact_page_url}...")
                    page.goto(contact_page_url, timeout=20000, wait_until="domcontentloaded")
                else:
                    logs.append("No obvious contact link discovered. Remaining on home page.")

            # Try locating form again
            forms = page.locator("form")
            logs.append(f"Found {forms.count()} form(s) on page.")
            
            if forms.count() == 0:
                # If still no form, let's create a visual log & screenshot for failure
                logs.append("[Failed] No form elements discovered on this website.")
                screenshot_name = f"fail_{uuid.uuid4().hex}.png"
                screenshot_path = media_dir / screenshot_name
                page.screenshot(path=str(screenshot_path))
                screenshot_filename = f"outreach_screenshots/{screenshot_name}"
                browser.close()
                return False, logs, screenshot_filename
            
            # Select the largest or first form
            target_form = forms.first
            logs.append("Selecting target form for automated submission...")
            
            # Find input elements
            inputs = target_form.locator("input, textarea, select")
            logs.append(f"Analyzing {inputs.count()} form field(s)...")
            
            filled_fields = []
            
            for i in range(inputs.count()):
                field = inputs.nth(i)
                name_attr = (field.get_attribute("name") or "").lower()
                id_attr = (field.get_attribute("id") or "").lower()
                type_attr = (field.get_attribute("type") or "").lower()
                placeholder_attr = (field.get_attribute("placeholder") or "").lower()
                aria_attr = (field.get_attribute("aria-label") or "").lower()
                
                # Check for visibility and accessibility
                if not field.is_visible():
                    continue
                if type_attr in ["submit", "button", "hidden", "checkbox", "radio"]:
                    continue
                
                # Combine search tokens to match fields
                combined_tokens = f"{name_attr} {id_attr} {placeholder_attr} {aria_attr}"
                
                # 1. Email field
                if "email" in type_attr or "email" in name_attr or "email" in combined_tokens or "mail" in name_attr:
                    field.fill(agency_info['email'])
                    filled_fields.append(f"Email -> {agency_info['email']}")
                
                # 2. Name field
                elif "name" in combined_tokens or "fullname" in combined_tokens or "first" in combined_tokens or "last" in combined_tokens:
                    field.fill(agency_info['name'])
                    filled_fields.append(f"Name -> {agency_info['name']}")
                
                # 3. Phone field
                elif "phone" in combined_tokens or "tel" in combined_tokens or "mobile" in combined_tokens or "phone" in type_attr:
                    field.fill(agency_info['phone'])
                    filled_fields.append(f"Phone -> {agency_info['phone']}")
                
                # 4. Subject field
                elif "subject" in combined_tokens or "title" in combined_tokens or "reason" in combined_tokens:
                    field.fill(subject)
                    filled_fields.append(f"Subject -> {subject}")
                
                # 5. Message field
                elif "message" in combined_tokens or "body" in combined_tokens or "comment" in combined_tokens or "text" in combined_tokens or field.evaluate("el => el.tagName") == "TEXTAREA":
                    field.fill(body)
                    filled_fields.append("Message Body -> [Generated Email]")
                    
                # 6. Fallback - if name is empty and field looks like text
                elif type_attr == "text" and not any(f.startswith("Name") for f in filled_fields):
                    field.fill(agency_info['name'])
                    filled_fields.append(f"Name (fallback) -> {agency_info['name']}")

            logs.append(f"Filled fields: {', '.join(filled_fields)}")
            
            # Look for submit button
            submit_btn = target_form.locator("button[type='submit'], input[type='submit']").first
            
            if submit_btn.count() == 0:
                # Search for any button containing "send" or "submit" inside the form
                buttons = target_form.locator("button, input")
                for j in range(buttons.count()):
                    btn = buttons.nth(j)
                    btn_text = (btn.text_content() or btn.get_attribute("value") or "").lower()
                    if "send" in btn_text or "submit" in btn_text or "apply" in btn_text or "book" in btn_text:
                        submit_btn = btn
                        break
            
            if submit_btn.count() == 0:
                # Last resort: just use the first button inside the form
                submit_btn = target_form.locator("button").first
                
            logs.append("[4/4] Submitting form...")
            
            # Click and wait for network idle or navigation
            submit_btn.click()
            page.wait_for_timeout(3000)  # Wait short duration for submission handler to kick off
            
            # Capture the screenshot of the confirmation page
            screenshot_name = f"success_{uuid.uuid4().hex}.png"
            screenshot_path = media_dir / screenshot_name
            page.screenshot(path=str(screenshot_path))
            screenshot_filename = f"outreach_screenshots/{screenshot_name}"
            
            logs.append("[Success] Auto-Apply Model successfully submitted form and captured screenshot.")
            browser.close()
            return True, logs, screenshot_filename
            
    except Exception as e:
        logs.append(f"[Error] Exception occurred in Playwright automation: {str(e)}")
        # Take an error screenshot if page context exists
        try:
            screenshot_name = f"error_{uuid.uuid4().hex}.png"
            screenshot_path = media_dir / screenshot_name
            page.screenshot(path=str(screenshot_path))
            screenshot_filename = f"outreach_screenshots/{screenshot_name}"
        except:
            pass
        return False, logs, screenshot_filename
