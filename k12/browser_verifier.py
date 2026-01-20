"""K12 Browser-Based Verifier - Avoids Session Mismatch

Uses Playwright browser throughout entire verification flow:
1. Navigate to ChatGPT Education page
2. Click verify button → Get fresh verificationId (SAME session)
3. Fill form, upload doc, poll status (SAME session)
4. Return redirect URL

No more "link expired" errors because everything uses same browser session.
"""
import re
import random
import logging
import time
from typing import Dict, Optional
from pathlib import Path

# Import from local modules
try:
    from . import config
    from .name_generator import generate_teacher_info, PRIORITY_DISTRICTS
    from .img_generator import generate_teacher_png, TeacherDocumentData
except ImportError:
    import config
    from name_generator import generate_teacher_info, PRIORITY_DISTRICTS
    from img_generator import generate_teacher_png, TeacherDocumentData

# Priority district templates
DISTRICT_TEMPLATES = ["nyc_doe", "miami_dade", "springfield_high"]

# Config
PROGRAM_ID = config.PROGRAM_ID
SHEERID_BASE_URL = config.SHEERID_BASE_URL
SCHOOLS = config.SCHOOLS
DEFAULT_SCHOOL_ID = config.DEFAULT_SCHOOL_ID

# ChatGPT Education verification URLs
CHATGPT_EDU_URL = "https://openai.com/chatgpt/education/"
SHEERID_VERIFY_URL = f"https://services.sheerid.com/verify/{PROGRAM_ID}/"

# Timing
MAX_WAIT_TIME = 900  # 15 minutes max
POLL_INTERVALS = [15, 15, 30, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60]  # Progressive

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


class BrowserVerifier:
    """Browser-based SheerID K12 Teacher Verifier.
    
    Uses Playwright to maintain single browser session throughout verification,
    avoiding "link expired" errors caused by session/fingerprint mismatch.
    """
    
    def __init__(self, custom_email: str = None, headless: bool = True):
        """
        Args:
            custom_email: Optional user email for SheerID confirmation
            headless: Run browser in headless mode (default True for server)
        """
        self.custom_email = custom_email
        self.headless = headless
        self.verification_id = None
        self.browser = None
        self.context = None
        self.page = None
        
    def _setup_browser(self):
        """Initialize Playwright browser with realistic settings."""
        from playwright.sync_api import sync_playwright
        
        self.playwright = sync_playwright().start()
        
        # Use Chromium with realistic settings
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        # Create context with realistic viewport and user agent
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )
        
        self.page = self.context.new_page()
        logger.info("✓ Browser initialized")
        
    def _cleanup_browser(self):
        """Close browser and cleanup resources."""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if hasattr(self, 'playwright'):
                self.playwright.stop()
            logger.info("✓ Browser cleaned up")
        except Exception as e:
            logger.error(f"Browser cleanup error: {e}")
    
    def _get_fresh_verification_id(self) -> str:
        """Navigate to SheerID verify page and get fresh verification ID."""
        logger.info(f"📍 Navigating to SheerID verify page...")
        
        # Go directly to SheerID verify URL
        self.page.goto(SHEERID_VERIFY_URL, wait_until='networkidle', timeout=30000)
        time.sleep(2)
        
        # Get current URL which should contain verificationId
        current_url = self.page.url
        logger.info(f"Current URL: {current_url}")
        
        # Extract verificationId
        match = re.search(r'verificationId=([a-f0-9]+)', current_url, re.IGNORECASE)
        if match:
            self.verification_id = match.group(1)
            logger.info(f"✓ Got verificationId: {self.verification_id}")
            return self.verification_id
        
        # Try to find it in page content or redirect
        time.sleep(2)
        current_url = self.page.url
        match = re.search(r'verificationId=([a-f0-9]+)', current_url, re.IGNORECASE)
        if match:
            self.verification_id = match.group(1)
            logger.info(f"✓ Got verificationId: {self.verification_id}")
            return self.verification_id

        # Try hidden input
        try:
            hidden_id = self.page.input_value('input[name="verificationId"]', timeout=2000)
            if hidden_id:
                self.verification_id = hidden_id
                logger.info(f"✓ Got verificationId from hidden input: {self.verification_id}")
                return self.verification_id
        except:
            pass

        logger.warning("Could not get verification ID from page/URL - proceeding anyway")
        self.verification_id = "UNKNOWN_ID"
        return self.verification_id
    
    def _fill_teacher_form(self, teacher_data: Dict) -> bool:
        """Fill in the teacher verification form."""
        logger.info("📝 Filling teacher form...")
        
        try:
            # Wait for form to load
            self.page.wait_for_selector('input[name="firstName"]', timeout=10000)
            
            # Fill form fields
            self.page.fill('input[name="firstName"]', teacher_data['first_name'])
            time.sleep(random.uniform(0.3, 0.7))
            
            self.page.fill('input[name="lastName"]', teacher_data['last_name'])
            time.sleep(random.uniform(0.3, 0.7))
            
            self.page.fill('input[name="email"]', teacher_data['email'])
            time.sleep(random.uniform(0.3, 0.7))
            
            # Birth date (format: YYYY-MM-DD)
            birth_date = teacher_data['birth_date']
            self.page.fill('input[name="birthDate"]', birth_date)
            time.sleep(random.uniform(0.3, 0.7))
            
            # School/Organization - search and select
            school_name = teacher_data['school_name']
            org_input = self.page.locator('input[name="organization"]')
            if org_input.count() > 0:
                org_input.fill(school_name[:20])  # First 20 chars to trigger search
                time.sleep(1.5)
                # Click first result
                self.page.locator('.sid-org-result').first.click()
                time.sleep(0.5)
            
            logger.info("✓ Form filled")
            return True
            
        except Exception as e:
            logger.error(f"Form fill error: {e}")
            return False
    
    def _submit_form(self) -> str:
        """Submit the form and return next step."""
        logger.info("📨 Submitting form...")
        
        try:
            # Find and click submit button
            submit_btn = self.page.locator('button[type="submit"]').first
            submit_btn.click()
            
            # Wait for next step
            time.sleep(3)
            
            # Check current step from page
            current_url = self.page.url
            
            # Look for SSO skip or doc upload
            if 'sso' in current_url.lower() or self.page.locator('.sid-sso-form').count() > 0:
                return 'sso'
            
            if 'docUpload' in current_url or self.page.locator('input[type="file"]').count() > 0:
                return 'docUpload'
            
            if 'success' in current_url.lower():
                return 'success'
                
            return 'unknown'
            
        except Exception as e:
            logger.error(f"Submit error: {e}")
            raise
    
    def _skip_sso(self):
        """Skip SSO step if present."""
        logger.info("⏭️ Skipping SSO...")
        try:
            # Look for "skip" or "use document" button
            skip_btn = self.page.locator('text=upload a document').first
            if skip_btn.count() > 0:
                skip_btn.click()
                time.sleep(2)
                logger.info("✓ SSO skipped")
        except Exception as e:
            logger.warning(f"SSO skip: {e}")
    
    def _upload_document(self, document_path: Path) -> bool:
        """Upload pre-generated teacher document."""
        logger.info("📄 Uploading document...")
        
        try:
            if not document_path.exists():
                logger.error(f"Document file not found: {document_path}")
                return False
                
            # Find file input and upload
            file_input = self.page.locator('input[type="file"]').first
            file_input.set_input_files(str(document_path))
            
            time.sleep(2)
            
            # Click upload/submit button
            submit_btn = self.page.locator('button[type="submit"]').first
            if submit_btn.count() > 0:
                submit_btn.click()
                time.sleep(3)
            
            logger.info("✓ Document uploaded")
            return True
            
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return False
    
    def _poll_for_result(self) -> Dict:
        """Poll page for verification result."""
        logger.info("⏳ Polling for result...")
        
        total_time = 0
        for i, interval in enumerate(POLL_INTERVALS):
            time.sleep(interval)
            total_time += interval
            
            # Refresh page to check status
            self.page.reload()
            time.sleep(2)
            
            current_url = self.page.url
            page_content = self.page.content().lower()
            
            logger.info(f"Check {i+1}: waited {total_time}s")
            
            # Check for success
            if 'success' in current_url or 'approved' in page_content or 'verified' in page_content:
                # Try to find redirect URL
                redirect_url = None
                links = self.page.locator('a[href*="openai"]').all()
                for link in links:
                    href = link.get_attribute('href')
                    if href and 'openai' in href:
                        redirect_url = href
                        break
                
                return {
                    'approved': True,
                    'redirect_url': redirect_url,
                    'total_time': total_time
                }
            
            # Check for rejection
            if 'rejected' in page_content or 'denied' in page_content:
                return {
                    'approved': False,
                    'rejected': True,
                    'total_time': total_time
                }
        
        return {
            'approved': None,
            'timeout': True,
            'total_time': total_time
        }
    
    def verify(self) -> Dict:
        """
        Run full browser-based verification flow.
        
        Returns:
            Dict with success status, redirect_url, teacher_info, etc.
        """
        try:
            # self._setup_browser() - Moved to after document generation

            
            # Select random district template and get matching teacher
            district_template = random.choice(DISTRICT_TEMPLATES)
            teacher = generate_teacher_info(district=district_template)
            
            # Use custom email if provided
            email = self.custom_email if self.custom_email else teacher['email']
            
            teacher_data = {
                'first_name': teacher['first_name'],
                'last_name': teacher['last_name'],
                'email': email,
                'birth_date': teacher['birth_date'],
                'school_name': teacher.get('school_name') or 'Springfield High School',
                'district_template': district_template,
                # Enriched fields
                'position': teacher.get('position'),
                'hire_date': teacher.get('hire_date'),
                'department': teacher.get('department'),
                'employee_id': teacher.get('employee_id'),
                'annual_salary': teacher.get('annual_salary'),
                'salary_step': teacher.get('salary_step'),
                'pension_number': teacher.get('pension_number'),
            }
            
            teacher_info = {
                'name': f"{teacher_data['first_name']} {teacher_data['last_name']}",
                'email': teacher_data['email'],
                'birth_date': teacher_data['birth_date'],
                'school': teacher_data['school_name'],
            }
            
            logger.info(f"{'='*50}")
            logger.info("BROWSER-BASED K12 VERIFICATION")
            logger.info(f"Teacher: {teacher_info['name']}")
            logger.info(f"Email: {teacher_info['email']}")
            logger.info(f"School: {teacher_info['school']}")
            logger.info(f"{'='*50}")

            # Step 0: PRE-GENERATE DOCUMENT (Avoids Playwright conflict)
            logger.info("📄 Pre-generating document...")
            from .img_generator import TeacherDocumentData
            
            shared_data = TeacherDocumentData(
                teacher_data['first_name'], 
                teacher_data['last_name'],
                school_name=teacher_data.get('school_name'),
                school_template=teacher_data.get('district_template'),
                position=teacher_data.get('position'),
                hire_date=teacher_data.get('hire_date'),
                employee_id=teacher_data.get('employee_id'),
                annual_salary=teacher_data.get('annual_salary'),
                salary_step=teacher_data.get('salary_step'),
                department=teacher_data.get('department'),
                pension_number=teacher_data.get('pension_number'),
            )
            
            png_data = generate_teacher_png(
                teacher_data['first_name'],
                teacher_data['last_name'],
                teacher_data['school_name'],
                doc_type='id_card',
                shared_data=shared_data,
                school_template=teacher_data.get('district_template')
            )
            
            temp_doc_path = Path(__file__).parent / f"temp_{random.randint(1000,9999)}.png"
            with open(temp_doc_path, 'wb') as f:
                f.write(png_data)
            logger.info(f"✓ Document saved to {temp_doc_path}")
            
            # Step 1: Initialize Browser & Get ID
            self._setup_browser()
            self._get_fresh_verification_id()
            
            # Step 2: Fill form
            if not self._fill_teacher_form(teacher_data):
                raise Exception("Failed to fill form")
            
            # Step 3: Submit form
            next_step = self._submit_form()
            
            if next_step == 'success':
                logger.info("✅ Instant approval!")
                return {
                    'success': True,
                    'current_step': 'success',
                    'verification_id': self.verification_id,
                    'teacher_info': teacher_info,
                }
            
            # Step 4: Skip SSO if needed
            if next_step == 'sso':
                self._skip_sso()
            
            # Step 5: Upload document
            # Step 5: Upload document
            if not self._upload_document(temp_doc_path):
                raise Exception("Failed to upload document")
            
            # Step 6: Poll for result
            result = self._poll_for_result()
            
            if result.get('approved'):
                logger.info("✅ APPROVED!")
                return {
                    'success': True,
                    'current_step': 'success',
                    'verification_id': self.verification_id,
                    'redirect_url': result.get('redirect_url'),
                    'teacher_info': teacher_info,
                }
            
            if result.get('rejected'):
                # Try blank image trick
                logger.info("❌ Rejected, skipping retry in this mode")
                # Removed retry loop for now to simplify flow
                # for i in range(3):
                #     self._upload_document(temp_doc_path)
                #     time.sleep(5)
                
                return {
                    'success': False,
                    'rejected': True,
                    'verification_id': self.verification_id,
                    'teacher_info': teacher_info,
                }
            
            # Timeout
            return {
                'success': False,
                'timeout': True,
                'verification_id': self.verification_id,
                'teacher_info': teacher_info,
            }
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {
                'success': False,
                'message': str(e),
                'verification_id': self.verification_id,
                'teacher_info': teacher_info if 'teacher_info' in locals() else {},
            }
            
        finally:
            self._cleanup_browser()
            # Cleanup temp file
            if 'temp_doc_path' in locals() and temp_doc_path.exists():
                try:
                    temp_doc_path.unlink()
                except:
                    pass


def verify_with_browser(custom_email: str = None, headless: bool = True) -> Dict:
    """
    Convenience function to run browser-based verification.
    
    Args:
        custom_email: Optional user email for SheerID confirmation
        headless: Run browser in headless mode
        
    Returns:
        Verification result dict
    """
    verifier = BrowserVerifier(custom_email=custom_email, headless=headless)
    return verifier.verify()


if __name__ == "__main__":
    # Test
    print("Testing Browser-Based K12 Verifier")
    print("=" * 50)
    
    result = verify_with_browser(headless=False)  # Show browser for testing
    print(f"\nResult: {result}")
