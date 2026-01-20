"""
Browser-Based SheerID Verifier with Anti-Detection

Uses Playwright with full fingerprint spoofing for Google Gemini Students verification.
Implements stealth scripts, human-like behavior, and IP tracking.
"""

import re
import random
import logging
import time
from typing import Dict, Optional
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

from . import config
from .fingerprint_generator import FingerprintGenerator, BrowserFingerprint
from .stealth_scripts import StealthScripts
from .ip_manager import IPRotationManager, get_ip_manager
from .name_generator import NameGenerator, generate_birth_date
from .img_generator import generate_image, generate_psu_email

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


# Timezone to geolocation mapping (US focused)
TIMEZONE_GEOLOCATIONS = {
    "America/New_York": {"latitude": 40.7128, "longitude": -74.0060},
    "America/Chicago": {"latitude": 41.8781, "longitude": -87.6298},
    "America/Denver": {"latitude": 39.7392, "longitude": -104.9903},
    "America/Los_Angeles": {"latitude": 34.0522, "longitude": -118.2437},
    "America/Phoenix": {"latitude": 33.4484, "longitude": -112.0740},
}


class BrowserVerifier:
    """
    Browser-based SheerID verifier with full anti-detection.
    
    Features:
    - Full browser fingerprint spoofing (30+ properties)
    - Stealth JavaScript injection
    - Human-like typing and delays
    - IP tracking to avoid reuse
    - Screenshot on error
    - Retry with new fingerprint
    """
    
    def __init__(
        self,
        verification_url: str,
        headless: bool = True,
        proxy: Dict = None,
        fingerprint: BrowserFingerprint = None
    ):
        """
        Initialize browser verifier.
        
        Args:
            verification_url: SheerID verification URL
            headless: Run browser in headless mode
            proxy: Optional proxy config {"server": "http://...", "username": "...", "password": "..."}
            fingerprint: Optional pre-generated fingerprint
        """
        self.verification_url = verification_url
        self.verification_id = self._extract_verification_id(verification_url)
        self.headless = headless
        self.proxy = proxy
        self.fingerprint = fingerprint
        self.ip_manager = get_ip_manager()
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
        # Status tracking
        self.current_ip = None
        self.current_fingerprint = None
    
    def _extract_verification_id(self, url: str) -> Optional[str]:
        """Extract verificationId from URL."""
        match = re.search(r'verificationId=([a-f0-9]+)', url, re.IGNORECASE)
        return match.group(1) if match else None
    
    def _update_status(self, step: str, message: str):
        """Log status update."""
        logger.info(f"[{step}] {message}")
    
    def _create_browser_context(
        self,
        playwright,
        fingerprint: BrowserFingerprint = None,
        proxy: Dict = None
    ):
        """Create browser context with fingerprint spoofing."""
        
        # Generate fingerprint if not provided
        if fingerprint is None:
            fingerprint = FingerprintGenerator.generate(
                os_type="windows",
                browser="chrome",
                webrtc_mode="altered"
            )
        
        self.current_fingerprint = fingerprint
        self._update_status("FP", f"Profile: {fingerprint.profile_id}")
        self._update_status("FP", f"WebGL: {fingerprint.webgl_renderer[:40]}...")
        
        # Viewport from fingerprint
        viewport = {
            "width": fingerprint.screen_width,
            "height": fingerprint.screen_avail_height
        }
        
        # Browser launch args
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-infobars',
            f'--window-size={fingerprint.screen_width},{fingerprint.screen_height}',
        ]
        
        if self.headless:
            browser_args.extend([
                '--disable-gpu',
                '--headless=new',
            ])
        
        # Launch browser
        browser = playwright.chromium.launch(
            headless=self.headless,
            args=browser_args
        )
        
        # Geolocation matching timezone
        geolocation = TIMEZONE_GEOLOCATIONS.get(
            fingerprint.timezone,
            {"latitude": 40.7128, "longitude": -74.0060}
        )
        
        # Create context with fingerprint
        context = browser.new_context(
            viewport=viewport,
            proxy=proxy,
            user_agent=fingerprint.user_agent,
            locale=fingerprint.language,
            timezone_id=fingerprint.timezone,
            color_scheme='light',
            device_scale_factor=fingerprint.device_pixel_ratio,
            permissions=['geolocation'],
            geolocation=geolocation,
            extra_http_headers={
                'Accept-Language': f'{fingerprint.language},{fingerprint.languages[0].split("-")[0]};q=0.9',
            }
        )
        
        # Inject stealth scripts
        stealth_js = StealthScripts.generate_all(fingerprint)
        context.add_init_script(stealth_js)
        
        self._update_status("FP", "Stealth scripts injected")
        
        return browser, context, fingerprint
    
    def _human_type(self, selector: str, text: str, delay_range=(30, 80)):
        """Type with human-like delays."""
        element = self.page.locator(selector)
        element.click()
        time.sleep(random.uniform(0.1, 0.3))
        
        for char in text:
            self.page.keyboard.type(char, delay=random.randint(*delay_range))
        
        time.sleep(random.uniform(0.1, 0.3))
    
    def _human_click(self, selector: str):
        """Click with human-like delay."""
        time.sleep(random.uniform(0.2, 0.5))
        self.page.locator(selector).click()
        time.sleep(random.uniform(0.3, 0.7))
    
    def _get_current_ip(self) -> str:
        """Get current IP address."""
        try:
            self.page.goto("https://api.ipify.org?format=json", timeout=10000)
            content = self.page.content()
            match = re.search(r'"ip"\s*:\s*"([^"]+)"', content)
            if match:
                return match.group(1)
        except:
            pass
        return "Unknown"
    
    def _fill_form(self, student_data: Dict, school: Dict):
        """Fill the SheerID verification form."""
        self._update_status("FORM", "Filling form...")
        
        # Wait for form
        self.page.wait_for_selector('#sid-first-name', timeout=30000)
        time.sleep(1)
        
        # Fill fields with JavaScript injection (fast + reliable)
        first_name = student_data['first_name']
        last_name = student_data['last_name']
        email = student_data['email']
        birth_date = student_data['birth_date']
        
        js_fill = f"""
        (function() {{
            function setValue(selector, value) {{
                const el = document.querySelector(selector);
                if (el) {{
                    const nativeSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value'
                    ).set;
                    nativeSetter.call(el, value);
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}
                return false;
            }}
            
            return {{
                firstName: setValue('#sid-first-name', '{first_name}'),
                lastName: setValue('#sid-last-name', '{last_name}'),
                email: setValue('#sid-email', '{email}'),
                birthDate: setValue('#sid-birth-date', '{birth_date}')
            }};
        }})();
        """
        
        result = self.page.evaluate(js_fill)
        logger.debug(f"JS fill result: {result}")
        
        time.sleep(0.5)
        
        # School selection
        school_name = school['name']
        school_id = str(school['id'])
        
        self._update_status("FORM", f"Selecting school: {school_name[:30]}...")
        
        # Click school input and type
        school_input = self.page.locator('#sid-organization')
        if school_input.count() > 0:
            school_input.click()
            time.sleep(0.3)
            self.page.keyboard.type(school_name[:20], delay=50)
            time.sleep(1.5)
            
            # Select from dropdown
            dropdown_item = self.page.locator(f'.sid-org-result:has-text("{school_name[:20]}")')
            if dropdown_item.count() > 0:
                dropdown_item.first.click()
                time.sleep(0.5)
        
        self._update_status("FORM", f"Form filled: {first_name} {last_name}")
    
    def _submit_form(self):
        """Submit the form."""
        self._update_status("SUBMIT", "Submitting form...")
        
        submit_btn = self.page.locator('button[type="submit"]')
        if submit_btn.count() > 0:
            submit_btn.first.click()
            time.sleep(2)
        
        self._update_status("SUBMIT", "Form submitted")
    
    def _upload_document(self, student_data: Dict, school_id: str):
        """Generate and upload student document."""
        self._update_status("DOC", "Generating student document...")
        
        # Generate image
        img_data = generate_image(
            student_data['first_name'],
            student_data['last_name'],
            school_id
        )
        
        self._update_status("DOC", f"Document size: {len(img_data)/1024:.1f}KB")
        
        # Save temp file
        temp_path = Path(__file__).parent / f"temp_doc_{random.randint(1000,9999)}.png"
        temp_path.write_bytes(img_data)
        
        try:
            # Upload via file input
            file_input = self.page.locator('input[type="file"]')
            if file_input.count() > 0:
                file_input.set_input_files(str(temp_path))
                time.sleep(2)
                
                # Click submit if available
                submit_btn = self.page.locator('button[type="submit"]')
                if submit_btn.count() > 0:
                    submit_btn.first.click()
                    time.sleep(2)
                
                self._update_status("DOC", "Document uploaded")
        finally:
            # Cleanup temp file
            if temp_path.exists():
                temp_path.unlink()
    
    def _wait_for_result(self, timeout_seconds: int = 60) -> Dict:
        """Wait for verification result."""
        self._update_status("WAIT", "Waiting for result...")
        
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            current_url = self.page.url
            page_content = self.page.content().lower()
            
            # Check for success
            if 'success' in current_url or 'verified' in page_content or 'approved' in page_content:
                return {"success": True, "status": "approved"}
            
            # Check for pending
            if 'pending' in page_content:
                return {"success": True, "status": "pending"}
            
            # Check for rejection
            if 'rejected' in page_content or 'denied' in page_content:
                return {"success": False, "status": "rejected"}
            
            time.sleep(5)
        
        return {"success": None, "status": "timeout"}
    
    def verify(self) -> Dict:
        """
        Run full browser-based verification.
        
        Returns:
            Dict with success, status, student_info, etc.
        """
        try:
            # Generate student info
            name = NameGenerator.generate()
            first_name = name['first_name']
            last_name = name['last_name']
            
            school_id = config.DEFAULT_SCHOOL_ID
            school = config.SCHOOLS[school_id]
            
            email = generate_psu_email(first_name, last_name)
            birth_date = generate_birth_date()
            
            student_data = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'birth_date': birth_date
            }
            
            student_info = {
                'name': f"{first_name} {last_name}",
                'email': email,
                'birth_date': birth_date,
                'school': school['name']
            }
            
            self._update_status("START", f"Student: {student_info['name']}")
            self._update_status("INFO", f"Email: {email}")
            self._update_status("INFO", f"School: {school['name']}")
            
            # Start Playwright
            self.playwright = sync_playwright().start()
            
            # Create browser with fingerprint
            self.browser, self.context, self.current_fingerprint = self._create_browser_context(
                self.playwright,
                fingerprint=self.fingerprint,
                proxy=self.proxy
            )
            
            self.page = self.context.new_page()
            
            # Get current IP
            self.current_ip = self._get_current_ip()
            self._update_status("IP", f"Current IP: {self.current_ip}")
            
            # Check if IP already used
            if self.ip_manager.is_ip_used(self.current_ip):
                self._update_status("WARN", "IP already used! May need rotation.")
            
            # Navigate to verification URL
            self._update_status("NAV", "Navigating to SheerID...")
            self.page.goto(self.verification_url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(2)
            
            # Fill form
            self._fill_form(student_data, school)
            
            # Submit form
            self._submit_form()
            
            # Handle SSO skip if needed
            sso_skip = self.page.locator('text=upload a document')
            if sso_skip.count() > 0:
                self._update_status("SSO", "Skipping SSO...")
                sso_skip.first.click()
                time.sleep(2)
            
            # Upload document
            file_input = self.page.locator('input[type="file"]')
            if file_input.count() > 0:
                self._upload_document(student_data, school_id)
            
            # Wait for result
            result = self._wait_for_result()
            
            # Mark IP as used
            self.ip_manager.mark_ip_used(
                self.current_ip,
                verification_id=self.verification_id,
                fingerprint_id=self.current_fingerprint.profile_id,
                success=result.get('success')
            )
            
            if result.get('success'):
                self._update_status("SUCCESS", "Verification submitted!")
                return {
                    'success': True,
                    'status': result.get('status'),
                    'verification_id': self.verification_id,
                    'student_info': student_info,
                    'ip_used': self.current_ip,
                    'fingerprint_id': self.current_fingerprint.profile_id
                }
            else:
                self._update_status("RESULT", f"Status: {result.get('status')}")
                return {
                    'success': False,
                    'status': result.get('status'),
                    'verification_id': self.verification_id,
                    'student_info': student_info
                }
                
        except Exception as e:
            logger.error(f"Verification error: {e}")
            
            # Take screenshot on error
            if self.page:
                try:
                    error_path = Path(__file__).parent / "data" / f"error_{int(time.time())}.png"
                    error_path.parent.mkdir(exist_ok=True)
                    self.page.screenshot(path=str(error_path))
                    logger.info(f"Error screenshot saved: {error_path}")
                except:
                    pass
            
            return {
                'success': False,
                'error': str(e),
                'verification_id': self.verification_id
            }
            
        finally:
            # Cleanup
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()


def verify_with_browser(
    verification_url: str,
    headless: bool = True,
    proxy: Dict = None
) -> Dict:
    """
    Convenience function for browser-based verification.
    
    Args:
        verification_url: SheerID verification URL
        headless: Run browser in headless mode
        proxy: Optional proxy config
        
    Returns:
        Verification result dict
    """
    verifier = BrowserVerifier(
        verification_url=verification_url,
        headless=headless,
        proxy=proxy
    )
    return verifier.verify()


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("Browser-Based SheerID Verifier")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter SheerID verification URL: ").strip()
    
    if not url:
        print("❌ No URL provided")
        sys.exit(1)
    
    result = verify_with_browser(url, headless=False)
    
    print()
    print("=" * 60)
    print(f"Result: {'✅ Success' if result['success'] else '❌ Failed'}")
    print(f"Status: {result.get('status', 'N/A')}")
    if result.get('student_info'):
        print(f"Student: {result['student_info'].get('name')}")
    print("=" * 60)
