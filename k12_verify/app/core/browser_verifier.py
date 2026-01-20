"""
Playwright Browser-based SheerID Verifier (Enhanced)

Uses real browser automation with advanced anti-detection:
- Full fingerprint spoofing (Canvas, WebGL, WebRTC, Audio)
- Human-like behavior (typing, clicking)
- Dynamic document generation
- Error screenshots
- Auto-retry with new fingerprint

Uses SYNC Playwright API to avoid async/sync mixing issues.
"""
import os
import re
import random
import asyncio
import logging
import traceback
import time
from typing import Dict, Optional, Callable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Import Playwright sync API
try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext
except ImportError:
    sync_playwright = None

# Import from existing modules
try:
    from .. import config as app_config
    from . import config
    from .name_generator import generate_teacher_info
    from .document_gen import generate_teacher_png, TeacherDocumentData, get_random_school_template
    from .fingerprint_generator import FingerprintGenerator, BrowserFingerprint
    from .stealth_scripts import StealthScripts
except ImportError:
    from app import config as app_config
    from app.core import config
    from app.core.name_generator import generate_teacher_info
    from app.core.document_gen import generate_teacher_png, TeacherDocumentData, get_random_school_template
    from app.core.fingerprint_generator import FingerprintGenerator, BrowserFingerprint
    from app.core.stealth_scripts import StealthScripts

import httpx  # For school search API

logger = logging.getLogger(__name__)

# Constants
SHEERID_BASE_URL = "https://services.sheerid.com"
DISTRICT_TEMPLATES = list(app_config.DISTRICTS.keys())
SCHOOLS = config.SCHOOLS
DEFAULT_SCHOOL_ID = config.DEFAULT_SCHOOL_ID

# SheerID School Search API (discovered via browser intercept)
SCHOOL_SEARCH_API = "https://orgsearch.sheerid.net/rest/organization/search"
SCHOOL_SEARCH_ACCOUNT_ID = "67d1dd27d7732a41eb64d141"  # ChatGPT program ID

# Timezone to Geolocation mapping (for fingerprint consistency)
TIMEZONE_GEOLOCATIONS = {
    "America/New_York": {"latitude": 40.7128, "longitude": -74.0060},      # NYC
    "America/Chicago": {"latitude": 41.8781, "longitude": -87.6298},       # Chicago
    "America/Los_Angeles": {"latitude": 34.0522, "longitude": -118.2437},  # LA
    "America/Denver": {"latitude": 39.7392, "longitude": -104.9903},       # Denver
    "America/Phoenix": {"latitude": 33.4484, "longitude": -112.0740},      # Phoenix
    "America/Anchorage": {"latitude": 61.2181, "longitude": -149.9003},    # Anchorage
    "Pacific/Honolulu": {"latitude": 21.3069, "longitude": -157.8583},     # Honolulu
}

# Load K12 schools for fast lookup by ID
K12_SCHOOLS_BY_ID = {}
K12_SCHOOLS_LIST = []
try:
    K12_SCHOOLS_FILE = Path(__file__).parent.parent.parent.parent / "k12" / "data" / "k12_schools.json"
    if K12_SCHOOLS_FILE.exists():
        import json
        with open(K12_SCHOOLS_FILE, 'r', encoding='utf-8') as f:
            K12_SCHOOLS_LIST = json.load(f)
            for school in K12_SCHOOLS_LIST:
                K12_SCHOOLS_BY_ID[school['id']] = school
        logger.info(f"Loaded {len(K12_SCHOOLS_BY_ID)} K12 schools")
except Exception as e:
    logger.warning(f"Could not load K12 schools: {e}")


def search_school_api(school_name: str, country: str = "US") -> Optional[Dict]:
    """
    Search for school using SheerID API directly.
    
    This is much faster than waiting for the browser dropdown to load.
    STRICT: Only returns K12 type, skip HIGH_SCHOOL entirely.
    
    Args:
        school_name: Name of school to search
        country: Country code (default: US)
        
    Returns:
        Dict with school id, name, type or None if not found (or only HIGH_SCHOOL)
    """
    try:
        params = {
            "accountId": SCHOOL_SEARCH_ACCOUNT_ID,
            "country": country,
            "name": school_name,
            "tags": "qualifying_hs,qualifying_k12",
            "type": "K12,HIGH_SCHOOL",
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        with httpx.Client(timeout=10) as client:
            response = client.get(SCHOOL_SEARCH_API, params=params, headers=headers)
            
            if response.status_code == 200:
                schools = response.json()
                if schools and len(schools) > 0:
                    # STRICT: Only return K12 type, never HIGH_SCHOOL
                    for school in schools:
                        if school.get('type') == 'K12':
                            return school
                    
                    # No K12 found - skip
                    logger.warning(f"No K12 found for '{school_name}', only HIGH_SCHOOL")
                    return None
        
        return None
    except Exception as e:
        logger.warning(f"School search API failed: {e}")
        return None


def get_school_search_query(school: Dict) -> str:
    """Build search query matching dropdown format: 'Name City, ST'"""
    name = school.get('name', '')[:25]
    city = school.get('city', '')
    state = school.get('state', '')
    
    if city and state:
        return f"{name} {city}, {state}"
    elif city:
        return f"{name} {city}"
    return name


class BrowserVerifier:
    """
    Verify SheerID using real browser automation (Playwright SYNC).
    
    Features:
    - Advanced fingerprint spoofing (Dolphin Browser-like)
    - Human-like typing and clicking behavior
    - Dynamic document generation
    - Error screenshots
    - Auto-retry with new fingerprint
    """
    
    def __init__(
        self,
        sheerid_url: str,
        custom_email: str = None,
        status_callback: Callable[[str, str], None] = None,
        headless: bool = True
    ):
        self.sheerid_url = sheerid_url
        self.custom_email = custom_email
        self.status_callback = status_callback
        self.headless = headless
        
        # Proxy config from environment
        self.proxy_host = os.getenv('PROXY_HOST', 'gw.dataimpulse.com')
        self.proxy_port = os.getenv('PROXY_PORT', '823')
        self.proxy_user = os.getenv('PROXY_USER', '')
        self.proxy_pass = os.getenv('PROXY_PASS', '')
        self.proxy_session = os.getenv('PROXY_SESSION', 'browser_verify')
        
        # Error screenshots directory
        self.screenshots_dir = Path(__file__).parent / "error_screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)
        
        # Current fingerprint (for retry logic)
        self.current_fingerprint: Optional[BrowserFingerprint] = None
    
    def _update_status(self, step: str, message: str):
        """Send status update."""
        if self.status_callback:
            self.status_callback(step, message)
        logger.info(f"[{step}] {message}")
    
    def _get_proxy_config(self) -> Optional[Dict]:
        """Get proxy configuration."""
        if not self.proxy_user or not self.proxy_host:
            return None
        
        # DataImpulse format with session
        username = f"{self.proxy_user}__cr.us-residential__sid.{self.proxy_session}_{random.randint(1000,9999)}"
        
        return {
            "server": f"http://{self.proxy_host}:{self.proxy_port}",
            "username": username,
            "password": self.proxy_pass
        }
    
    def _create_browser_context_sync(
        self, 
        playwright, 
        fingerprint: BrowserFingerprint = None
    ):
        """
        Create browser with advanced anti-detection fingerprint (SYNC version).
        
        Returns:
            Tuple of (browser, context, fingerprint)
        """
        proxy = self._get_proxy_config()
        
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
        
        # Browser launch args for anti-detection
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-infobars',
            '--disable-background-timer-throttling',
            '--disable-popup-blocking',
            '--disable-backgrounding-occluded-windows',
            f'--window-size={fingerprint.screen_width},{fingerprint.screen_height}',
        ]
        
        # Add headless-specific args
        if self.headless:
            browser_args.extend([
                '--disable-gpu',
                '--headless=new',  # New headless mode (less detectable)
            ])
        
        # Launch browser (SYNC)
        browser = playwright.chromium.launch(
            headless=self.headless,
            args=browser_args
        )
        
        # Get geolocation matching timezone
        geolocation = TIMEZONE_GEOLOCATIONS.get(
            fingerprint.timezone, 
            {"latitude": 40.7128, "longitude": -74.0060}  # Default NYC
        )
        
        # Create context with fingerprint settings (SYNC)
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
        
        # Generate and inject stealth scripts (SYNC)
        stealth_js = StealthScripts.generate_all(fingerprint)
        context.add_init_script(stealth_js)
        
        self._update_status("FP", "Stealth scripts injected")
        
        return browser, context, fingerprint
    
    # ============ HUMAN-LIKE BEHAVIOR ============
    
    def _human_type(self, page: Page, selector: str, text: str, clear_first: bool = True, fast_mode: bool = False):
        """
        Type text with human-like delays.
        
        Args:
            page: Playwright page
            selector: CSS selector for input
            text: Text to type
            clear_first: Whether to clear existing text first
            fast_mode: If True, use fill() instead of character-by-character typing
        """
        element = page.locator(selector).first
        
        # Short wait - element should already exist
        try:
            element.wait_for(state="attached", timeout=2000)  # Just check attached, not visible
        except Exception as e:
            logger.warning(f"Element {selector} not attached: {e}")
            # Try to continue anyway - element might work
        
        try:
            # Click to focus with short timeout
            element.click(timeout=2000)
            time.sleep(random.uniform(0.05, 0.1))
            
            if clear_first:
                # Select all and delete
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                time.sleep(random.uniform(0.02, 0.05))
            
            if fast_mode:
                # Fast mode - use fill() with explicit short timeout
                element.fill(text, timeout=3000)  # 3s max
            else:
                # Human-like mode - type character by character but faster
                for char in text:
                    page.keyboard.type(char, delay=random.randint(20, 60))  # Faster: 20-60ms per char
                    
                    # Occasional pause (3% chance - reduced from 5%)
                    if random.random() < 0.03:
                        time.sleep(random.uniform(0.1, 0.2))
        except Exception as e:
            logger.warning(f"Failed to type in {selector}: {e}")
            # Try keyboard type as fast fallback (no wait)
            try:
                page.keyboard.type(text, delay=10)  # Very fast typing
            except:
                pass
    
    def _human_click(self, page: Page, selector: str, timeout: int = 5000):
        """
        Click with human-like behavior (random offset + mouse movement).
        
        Args:
            page: Playwright page
            selector: CSS selector for element
            timeout: Max wait time in ms
        """
        try:
            element = page.locator(selector).first
            element.wait_for(timeout=timeout)
            
            # Get element bounding box
            box = element.bounding_box()
            if box:
                # Calculate random point within element (30-70% range)
                x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
                y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
                
                # Move mouse with steps (human-like curve)
                page.mouse.move(x, y, steps=random.randint(5, 15))
                time.sleep(random.uniform(0.05, 0.15))
                
                # Click
                page.mouse.click(x, y)
            else:
                # Fallback to direct click
                element.click()
                
            time.sleep(random.uniform(0.1, 0.3))
            return True
        except Exception as e:
            logger.debug(f"Human click failed for {selector}: {e}")
            return False
    
    def _random_scroll(self, page: Page):
        """Perform random scroll to simulate human browsing."""
        scroll_amount = random.randint(50, 200)
        page.mouse.wheel(0, scroll_amount)
        time.sleep(random.uniform(0.2, 0.5))
    
    # ============ DOCUMENT GENERATION ============
    
    def _generate_document(self, teacher_data: Dict, school: Dict) -> Optional[Path]:
        """
        Generate teacher document dynamically.
        
        Returns:
            Path to generated document or None if failed
        """
        self._update_status("DOC", "Generating document...")
        
        try:
            # Create document data
            doc_data = TeacherDocumentData(
                teacher_name=f"{teacher_data['first_name']} {teacher_data['last_name']}",
                school_name=school.get('name', 'School'),
                school_city=school.get('city', ''),
                school_state=school.get('state', ''),
                hire_date=teacher_data.get('birth_date', '2020-08-15'),  # Use as hire date
                job_title="Teacher",
                salary=random.randint(45000, 75000),
            )
            
            # Get random template
            template = get_random_school_template()
            
            # Generate PNG
            output_path = generate_teacher_png(doc_data, template)
            
            if output_path and Path(output_path).exists():
                self._update_status("DOC", f"Document generated: {Path(output_path).name}")
                return Path(output_path)
            
        except Exception as e:
            self._update_status("DOC", f"Generation failed: {str(e)[:50]}")
            logger.error(f"Document generation error: {e}")
        
        # Fallback to pre-made document
        return self._find_fallback_document()
    
    def _find_fallback_document(self) -> Optional[Path]:
        """Find pre-made document as fallback."""
        project_root = Path(__file__).parent.parent.parent.parent
        possible_paths = [
            Path(__file__).parent / "test_payslip.png",
            project_root / "k12" / "test_payslip.png",
            project_root / "test_payslip.png",
            Path(__file__).parent / "generated" / "*.png",
        ]
        
        for p in possible_paths:
            if p.exists():
                return p
            # Handle glob pattern
            if '*' in str(p):
                matches = list(p.parent.glob(p.name))
                if matches:
                    return matches[0]
        
        return None
    
    # ============ ERROR HANDLING ============
    
    def _take_error_screenshot(self, page: Page, error_type: str = "error"):
        """Take screenshot for debugging on error."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self.screenshots_dir / f"{error_type}_{timestamp}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            self._update_status("DEBUG", f"Screenshot: {screenshot_path.name}")
            return screenshot_path
        except Exception as e:
            logger.debug(f"Screenshot failed: {e}")
            return None
    
    # ============ FORM FILLING ============
    
    def _fill_form_sync(self, page: Page, teacher_data: Dict, school: Dict):
        """Fill the SheerID verification form (SYNC, JavaScript injection for speed)."""
        self._update_status("FORM", "Filling form...")
        
        # Wait for form to load
        page.wait_for_selector('#sid-first-name', timeout=30000)
        self._update_status("FORM", "Form loaded")
        
        # Small delay for React hydration
        time.sleep(0.5)
        
        # Use JavaScript injection to fill form fields instantly
        # This bypasses Playwright's element interaction which times out on SheerID
        first_name = teacher_data['first_name']
        last_name = teacher_data['last_name']
        email = teacher_data['email']
        
        js_fill_form = f"""
        (function() {{
            function setInputValue(selector, value) {{
                const input = document.querySelector(selector);
                if (input) {{
                    // Set native value
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value'
                    ).set;
                    nativeInputValueSetter.call(input, value);
                    
                    // Trigger React events
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    return true;
                }}
                return false;
            }}
            
            const results = {{
                firstName: setInputValue('#sid-first-name', '{first_name}'),
                lastName: setInputValue('#sid-last-name', '{last_name}'),
                email: setInputValue('#sid-email', '{email}')
            }};
            
            return results;
        }})();
        """
        
        try:
            result = page.evaluate(js_fill_form)
            logger.debug(f"JS fill result: {result}")
            
            # Small delay after JS fill
            time.sleep(0.3)
            
            # Verify fields were filled (optional check)
            if not all(result.values()):
                logger.warning(f"Some fields failed to fill via JS: {result}")
                # Fallback to keyboard typing for failed fields
                if not result.get('firstName'):
                    page.keyboard.type(first_name, delay=20)
                    page.keyboard.press('Tab')
                if not result.get('lastName'):
                    page.keyboard.type(last_name, delay=20)
                    page.keyboard.press('Tab')
                if not result.get('email'):
                    page.keyboard.type(email, delay=20)
        except Exception as e:
            logger.warning(f"JS fill failed, using keyboard fallback: {e}")
            # Ultimate fallback: just type into whatever is focused
            page.keyboard.type(first_name, delay=30)
            page.keyboard.press('Tab')
            time.sleep(0.1)
            page.keyboard.type(last_name, delay=30)
            page.keyboard.press('Tab')
            time.sleep(0.1)
            page.keyboard.type(email, delay=30)
        
        time.sleep(0.2)
        
        # School selection - use pre-loaded sheerid_school_id if available
        try:
            school_input = page.locator('#sid-teacher-school')
            if school_input.count() > 0:
                school_name = school.get('name', '')
                self._update_status("FORM", f"School: {school_name[:35]}...")
                
                # Check if teacher_data already has SheerID school ID (from enriched data)
                school_id = teacher_data.get('sheerid_school_id')
                school_display_name = teacher_data.get('sheerid_school_name', school_name)
                
                # If not in teacher_data, fall back to API lookup
                if not school_id:
                    api_school = search_school_api(school_name)
                    if api_school:
                        school_id = api_school.get('id')
                        school_display_name = api_school.get('name', school_name)
                
                if school_id:
                    self._update_status("FORM", f"School ID: {school_id}")
                    
                    # Use JavaScript to set the school value directly
                    # This bypasses the slow dropdown and sets the hidden value
                    js_set_school = f"""
                    (function() {{
                        const input = document.getElementById('sid-teacher-school');
                        if (input) {{
                            // Set visible value
                            input.value = "{school_display_name}";
                            
                            // Trigger React state update
                            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                                window.HTMLInputElement.prototype, 'value'
                            ).set;
                            nativeInputValueSetter.call(input, "{school_display_name}");
                            
                            // Dispatch events
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            
                            // Try to find and set the hidden organization ID field
                            const hiddenOrg = document.querySelector('input[name*="organization"], input[id*="organization"]');
                            if (hiddenOrg) {{
                                hiddenOrg.value = "{school_id}";
                            }}
                            
                            // Store in window for form submission
                            window._selectedOrganizationId = {school_id};
                        }}
                        return true;
                    }})();
                    """
                    page.evaluate(js_set_school)
                    time.sleep(0.3)
                    
                    # Also try clicking the dropdown to make it appear selected
                    try:
                        self._human_click(page, '#sid-teacher-school', timeout=2000)
                        time.sleep(0.2)
                        
                        # Type first few chars to trigger dropdown
                        for char in school_name[:8]:
                            page.keyboard.type(char, delay=random.randint(30, 60))
                        time.sleep(1)
                        
                        # Select first option if dropdown appears
                        try:
                            page.wait_for_selector('.sid-organization-list__item', timeout=2000)
                            page.keyboard.press("ArrowDown")
                            time.sleep(0.1)
                            page.keyboard.press("Enter")
                            self._update_status("FORM", "School selected from dropdown")
                        except:
                            # Dropdown didn't appear, but we already set via JS
                            self._update_status("FORM", "School set via API (no dropdown)")
                    except:
                        pass
                else:
                    # Fallback to manual typing if API fails
                    self._update_status("WARN", "API failed, using manual dropdown")
                    self._human_click(page, '#sid-teacher-school', timeout=3000)
                    time.sleep(0.2)
                    for char in school_name[:12]:
                        page.keyboard.type(char, delay=random.randint(30, 80))
                    time.sleep(2)
                    try:
                        page.wait_for_selector('.sid-organization-list__item', timeout=3000)
                        page.keyboard.press("ArrowDown")
                        page.keyboard.press("Enter")
                    except:
                        self._update_status("WARN", "Dropdown timeout")
                        
        except Exception as e:
            self._update_status("WARN", f"School: {str(e)[:40]}")
        
        # Close overlay
        page.keyboard.press("Escape")
        time.sleep(0.2)
        
        # Fill birth date if present
        try:
            birth_input = page.locator('#sid-birth-date, input[id*="birth"]')
            if birth_input.count() > 0:
                birth_input.first.fill(teacher_data.get('birth_date', '1985-05-15'))
        except:
            pass
        
        self._update_status("FORM", f"Form filled: {teacher_data['first_name']} {teacher_data['last_name']}")
    
    def _submit_form_sync(self, page: Page):
        """Submit the verification form (SYNC)."""
        self._update_status("SUBMIT", "Submitting form...")
        
        submit_selectors = [
            'button[type="submit"]',
            '.sid-submit-btn',
            'button.submit',
            'button:has-text("Verify")',
            'button:has-text("Submit")',
            'button:has-text("Continue")',
        ]
        
        for selector in submit_selectors:
            if self._human_click(page, selector, timeout=2000):
                self._update_status("SUBMIT", "Form submitted")
                time.sleep(2)
                return True
        
        # Fallback: press Enter
        self._update_status("SUBMIT", "Pressing Enter as fallback")
        page.keyboard.press("Enter")
        time.sleep(2)
        return True
    
    def _upload_document_sync(self, page: Page, teacher_data: Dict, school: Dict):
        """Upload teacher document if required (SYNC)."""
        self._update_status("DOC", "Checking if doc upload needed...")
        
        # Check for doc upload step
        try:
            page.wait_for_selector('input[type="file"], .file-upload', timeout=5000)
        except:
            self._update_status("DOC", "No doc upload required")
            return
        
        self._update_status("DOC", "Document upload required")
        
        # Generate document
        doc_path = self._generate_document(teacher_data, school)
        
        if not doc_path:
            self._update_status("DOC", "No document available - skipping")
            return
        
        # Upload file
        try:
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(str(doc_path))
            self._update_status("DOC", "Document uploaded")
        except Exception as e:
            self._update_status("DOC", f"Upload failed: {str(e)[:50]}")
            return
        
        # Submit doc
        time.sleep(1)
        submit_btn = page.locator('button[type="submit"], .submit-btn').first
        if submit_btn.count() > 0:
            self._human_click(page, 'button[type="submit"], .submit-btn')
    
    def _wait_for_result_sync(self, page: Page) -> Dict:
        """Wait for verification result (SYNC)."""
        self._update_status("POLL", "Waiting for result (max 30s)...")
        
        max_checks = 6  # 6 x 5s = 30s
        interval = 5
        
        for i in range(max_checks):
            time.sleep(interval)
            self._update_status("POLL", f"Check {i+1}/{max_checks}...")
            
            # Check for ChatGPT redirect
            current_url = page.url
            if 'chatgpt.com' in current_url or 'success' in current_url.lower():
                self._update_status("SUCCESS", "VERIFICATION SUCCESSFUL!")
                return {'success': True, 'redirectUrl': current_url}
            
            # Check for success element
            success_el = page.locator('.success, .verified, .sid-success')
            if success_el.count() > 0:
                self._update_status("SUCCESS", "VERIFICATION SUCCESSFUL!")
                return {'success': True, 'redirectUrl': page.url}
            
            # Check for pending
            pending_el = page.locator('.pending, .under-review')
            if pending_el.count() > 0:
                self._update_status("PENDING", "Document under review")
                return {'pending': True, 'message': 'Document submitted, under review'}
            
            # Check for error/rejection
            error_el = page.locator('.error, .rejected, .sid-error')
            if error_el.count() > 0:
                error_text = error_el.first.inner_text()[:100] if error_el.count() > 0 else "Unknown error"
                self._update_status("ERROR", f"Rejected: {error_text}")
                return {'success': False, 'rejected': True, 'message': error_text}
        
        # Timeout
        self._update_status("TIMEOUT", "Result check timed out")
        return {'success': False, 'timeout': True, 'message': 'Verification timed out'}
    
    # ============ MAIN VERIFICATION ============
    
    def _run_sync_verification(
        self, 
        teacher_data: Dict, 
        school: Dict,
        fingerprint: BrowserFingerprint = None
    ) -> Dict:
        """
        Run verification using SYNC Playwright.
        
        This is the main verification logic, fully synchronous.
        """
        if sync_playwright is None:
            return {'success': False, 'error': True, 'message': 'Playwright not installed'}
        
        browser = None
        playwright_instance = None
        page = None
        
        try:
            self._update_status("DEBUG", "Playwright starting...")
            playwright_instance = sync_playwright().start()
            
            # Create browser with anti-detection
            self._update_status("BROWSER", "Launching browser with fingerprint...")
            browser, context, fingerprint = self._create_browser_context_sync(
                playwright_instance, fingerprint
            )
            
            self._update_status("DEBUG", f"Profile: {fingerprint.profile_id}")
            
            # Create page
            page = context.new_page()
            page.set_default_timeout(15000)
            
            # Get current IP
            try:
                page.goto('https://api.ipify.org?format=json', timeout=15000)
                ip_text = page.inner_text('body')
                import json
                ip = json.loads(ip_text).get('ip', 'Unknown')
                self._update_status("CONN", f"Browser IP: {ip}")
            except:
                self._update_status("CONN", "Could not get IP")
            
            # Navigate to SheerID
            self._update_status("NAV", "Navigating to SheerID...")
            page.goto(self.sheerid_url, timeout=60000)
            time.sleep(random.uniform(1.5, 2.5))
            
            # Fill and submit form
            self._fill_form_sync(page, teacher_data, school)
            self._submit_form_sync(page)
            
            # Wait for redirect
            time.sleep(3)
            
            # Check if already redirected to ChatGPT
            current_url = page.url
            if 'chatgpt.com' in current_url:
                self._update_status("SUCCESS", "VERIFICATION SUCCESSFUL!")
                self._update_status("LINK", f"URL: {current_url}")
                return {'success': True, 'redirectUrl': current_url, 'teacher': teacher_data}
            
            # Check for doc upload
            self._upload_document_sync(page, teacher_data, school)
            
            # Wait for result
            result = self._wait_for_result_sync(page)
            result['teacher'] = teacher_data
            result['fingerprint_id'] = fingerprint.profile_id
            
            # Log final URL if success
            if result.get('success') and result.get('redirectUrl'):
                self._update_status("LINK", f"URL: {result['redirectUrl']}")
            
            return result
            
        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            tb = traceback.format_exc()
            self._update_status("ERROR", f"Error: {error_msg}")
            logger.error(f"Browser verification error: {tb}")
            
            # Take error screenshot
            if page:
                self._take_error_screenshot(page, "verification_error")
            
            return {'success': False, 'error': True, 'message': error_msg}
        
        finally:
            if browser:
                browser.close()
            if playwright_instance:
                playwright_instance.stop()
    
    async def verify(self, max_retries: int = 2) -> Dict:
        """
        Run browser verification with retry logic.
        
        Args:
            max_retries: Number of retries with new fingerprint on detection
            
        Returns:
            Dict with verification result
        """
        self._update_status("START", "Starting browser verification...")
        
        # Generate teacher data (returns single dict with all info)
        teacher_data = generate_teacher_info()
        if self.custom_email:
            teacher_data['email'] = self.custom_email
        
        # Extract school info from teacher data
        school = {
            'id': teacher_data.get('school_id', ''),
            'name': teacher_data.get('school_name', 'School'),
            'city': teacher_data.get('school_city', ''),
            'state': teacher_data.get('school_state', ''),
        }
        
        self._update_status("INFO", f"Teacher: {teacher_data['first_name']} {teacher_data['last_name']}")
        self._update_status("INFO", f"Email: {teacher_data['email']}")
        self._update_status("INFO", f"School: {school.get('name', 'Unknown')[:40]}")
        
        # Run sync Playwright in separate thread
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Generate new fingerprint for each attempt
                fingerprint = FingerprintGenerator.generate(
                    os_type="windows",
                    browser="chrome",
                    webrtc_mode="altered"
                )
                
                if attempt > 0:
                    self._update_status("RETRY", f"Attempt {attempt + 1}/{max_retries + 1} with new fingerprint...")
                
                result = await loop.run_in_executor(
                    executor,
                    self._run_sync_verification,
                    teacher_data,
                    school,
                    fingerprint
                )
                
                if result.get('success'):
                    return result
                
                # Check if fraud detected (retry with new fingerprint)
                error_msg = result.get('message', '').lower()
                if 'fraud' in error_msg or 'blocked' in error_msg or 'suspicious' in error_msg:
                    self._update_status("DETECT", "Detection suspected, retrying...")
                    last_error = result
                    time.sleep(random.uniform(3, 5))
                    continue
                
                # Other errors - don't retry
                return result
                
            except Exception as e:
                error_msg = str(e) or repr(e)
                tb = traceback.format_exc()
                self._update_status("ERROR", f"Error: {error_msg}")
                logger.error(f"Browser verification error: {tb}")
                last_error = {'success': False, 'error': True, 'message': error_msg}
        
        # All retries exhausted
        executor.shutdown(wait=False)
        return last_error or {'success': False, 'error': True, 'message': 'All retries exhausted'}


async def run_browser_verification(url: str, email: str = None, status_callback=None) -> Dict:
    """Convenience function to run browser verification."""
    verifier = BrowserVerifier(
        sheerid_url=url,
        custom_email=email,
        status_callback=status_callback
    )
    return await verifier.verify()
