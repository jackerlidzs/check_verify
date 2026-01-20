"""
URL-Based SheerID Verifier

Allows verification using just the SheerID URL (no cookies needed).
Extracts verificationId from URL and calls SheerID API directly.
"""
import re
import os
import time
import random
import httpx
import logging
from typing import Dict, Optional, Callable
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Import from existing modules
try:
    from .. import config as app_config
    from . import config
    from .name_generator import generate_teacher_info
    from .document_gen import generate_teacher_png, TeacherDocumentData, get_random_school_template
    from .verifier import generate_newrelic_headers, categorize_error, ERROR_ACTIONS
    from .mailtm_client import MailTmClient
except ImportError:
    from app import config as app_config
    from app.core import config
    from app.core.name_generator import generate_teacher_info
    from app.core.document_gen import generate_teacher_png, TeacherDocumentData, get_random_school_template
    from app.core.verifier import generate_newrelic_headers, categorize_error, ERROR_ACTIONS
    from app.core.mailtm_client import MailTmClient

logger = logging.getLogger(__name__)

# Constants
SHEERID_BASE_URL = "https://services.sheerid.com"
DISTRICT_TEMPLATES = list(app_config.DISTRICTS.keys())
SCHOOLS = config.SCHOOLS
DEFAULT_SCHOOL_ID = config.DEFAULT_SCHOOL_ID

# User-Agent pool for fingerprint rotation (matched with Cookie mode)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
]

# Screen resolutions for fingerprint (from Cookie mode)
SCREEN_RESOLUTIONS = [
    (1920, 1080), (1366, 768), (1536, 864), (1440, 900), 
    (1280, 720), (2560, 1440), (1680, 1050), (1600, 900)
]

# Timezones (US) for fingerprint
TIMEZONES = [
    'America/New_York', 'America/Chicago', 'America/Denver', 
    'America/Los_Angeles', 'America/Phoenix'
]


class URLVerifier:
    """
    Verify SheerID using just the verification URL.
    No cookies needed - creates fresh session via proxy.
    """
    
    def __init__(
        self,
        verification_url: str,
        custom_email: str = None,
        status_callback: Callable[[str, str], None] = None
    ):
        """
        Initialize URL-based verifier.
        
        Args:
            verification_url: SheerID verification URL (contains verificationId)
            custom_email: Optional custom email to use
            status_callback: Callback for status updates
        """
        self.verification_url = verification_url
        self.verification_id = self._extract_verification_id(verification_url)
        self.custom_email = custom_email
        self.status_callback = status_callback or (lambda x, y: None)
        
        # Device fingerprint
        self.device_fingerprint = self._generate_device_fingerprint()
        self.user_agent = random.choice(USER_AGENTS)
        
        # HTTP client with proxy
        self.http_client = self._create_http_client()
        
        # Get current IP
        self.current_ip, self.ip_country = self._get_current_ip()
        
        logger.info(f"URLVerifier initialized for ID: {self.verification_id[:20]}...")
    
    def _extract_verification_id(self, url: str) -> str:
        """
        Extract verificationId from URL.
        
        Supports formats:
        - https://services.sheerid.com/verify/PROGRAM_ID/?verificationId=XXX
        - https://www.sheerid.com/verify/...?verificationId=XXX
        """
        # Try query param first
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        if 'verificationId' in params:
            return params['verificationId'][0]
        
        # Try path-based ID (last segment)
        path_parts = parsed.path.strip('/').split('/')
        if path_parts:
            last_part = path_parts[-1]
            # Check if it looks like a verification ID (24 hex chars)
            if re.match(r'^[a-f0-9]{24}$', last_part):
                return last_part
        
        raise ValueError(f"Could not extract verificationId from URL: {url}")
    
    def _generate_device_fingerprint(self) -> str:
        """Generate random device fingerprint."""
        chars = '0123456789abcdef'
        return ''.join(random.choice(chars) for _ in range(32))
    
    def _get_random_browser_config(self) -> dict:
        """Generate random browser fingerprint config (matched with Cookie mode)."""
        ua = random.choice(USER_AGENTS)
        screen = random.choice(SCREEN_RESOLUTIONS)
        tz = random.choice(TIMEZONES)
        
        # Determine browser type from UA and generate matching Sec-Ch-Ua
        if 'Firefox' in ua:
            sec_ch_ua = '"Firefox";v="121"'
        elif 'Edg' in ua:
            sec_ch_ua = '"Microsoft Edge";v="120", "Chromium";v="120"'
        elif 'Safari' in ua and 'Chrome' not in ua:
            sec_ch_ua = '"Safari";v="17"'
        else:
            chrome_ver = '120' if '120' in ua else ('119' if '119' in ua else '121')
            sec_ch_ua = f'"Not_A Brand";v="8", "Chromium";v="{chrome_ver}", "Google Chrome";v="{chrome_ver}"'
        
        return {
            'user_agent': ua,
            'screen_width': screen[0],
            'screen_height': screen[1],
            'timezone': tz,
            'sec_ch_ua': sec_ch_ua,
            'platform': '"Windows"' if 'Windows' in ua else '"macOS"',
        }
    
    def _create_http_client(self) -> httpx.Client:
        """Create HTTP client with proxy if configured."""
        from dotenv import load_dotenv
        import socket
        
        load_dotenv(override=True)
        
        proxy_enabled = os.getenv('PROXY_ENABLED', 'false').lower() == 'true'
        proxy_url = None
        
        if proxy_enabled:
            proxy_host = os.getenv('PROXY_HOST', '')
            proxy_port = os.getenv('PROXY_PORT', '10000')
            proxy_user = os.getenv('PROXY_USER', '')
            proxy_pass = os.getenv('PROXY_PASS', '')
            proxy_session = os.getenv('PROXY_SESSION', 'default')
            
            if proxy_user and proxy_pass and proxy_host:
                # DataImpulse format with session
                username = f"{proxy_user}__sess.{proxy_session}"
                proxy_url = f"http://{username}:{proxy_pass}@{proxy_host}:{proxy_port}"
                self._update_status("PROXY", f"Using proxy: {proxy_host}:{proxy_port}")
        else:
            self._update_status("INFO", "[DIRECT MODE] No proxy configured")
        
        return httpx.Client(
            timeout=60.0,
            proxy=proxy_url,
            headers={
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
            }
        )
    
    def _get_current_ip(self) -> tuple:
        """Get current IP address via proxy."""
        try:
            resp = self.http_client.get('https://api.ipify.org?format=json')
            ip = resp.json().get('ip', 'Unknown')
            
            # Get country
            try:
                geo_resp = self.http_client.get(f'https://ipapi.co/{ip}/country/')
                country = geo_resp.text.strip()
            except:
                country = 'US'
            
            return ip, country
        except Exception as e:
            logger.warning(f"Could not get IP: {e}")
            return 'Unknown', 'US'
    
    def _update_status(self, step: str, message: str):
        """Send status update."""
        self.status_callback(step, message)
        logger.info(f"[{step}] {message}")
    
    def _get_country_flag(self, country_code: str) -> str:
        """Get flag emoji for country code."""
        flags = {
            'US': '🇺🇸', 'CA': '🇨🇦', 'GB': '🇬🇧', 'DE': '🇩🇪',
            'FR': '🇫🇷', 'AU': '🇦🇺', 'JP': '🇯🇵', 'VN': '🇻🇳',
        }
        return flags.get(country_code.upper(), '🌍')
    
    def _sheerid_request(self, method: str, url: str, body: Optional[Dict] = None) -> tuple:
        """Make request to SheerID API with anti-detection measures.
        
        Enhanced with techniques from military module + Cookie mode:
        - Dynamic browser fingerprint (UA, Sec-Ch-Ua, platform rotation)
        - NewRelic tracking headers
        - SheerID client version headers
        - Increased human-like delays
        """
        # Human-like delay (2-5s)
        time.sleep(random.uniform(2.0, 5.0))
        
        # Get random browser config for this request (matched with Cookie mode)
        browser_config = self._get_random_browser_config()
        
        # Generate NewRelic headers for anti-bot bypass
        nr_headers = generate_newrelic_headers()
        
        headers = {
            # Standard headers
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            
            # Dynamic browser fingerprint headers (from browser_config)
            'User-Agent': browser_config['user_agent'],
            'Sec-Ch-Ua': browser_config['sec_ch_ua'],
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': browser_config['platform'],
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Origin': SHEERID_BASE_URL,
            'Referer': f"{SHEERID_BASE_URL}/verify/",
            
            # SheerID client headers (from military module)
            'clientversion': '2.157.0',
            'clientname': 'jslib',
            
            # NewRelic tracking headers (anti-bot bypass)
            'newrelic': nr_headers['newrelic'],
            'traceparent': nr_headers['traceparent'],
            'tracestate': nr_headers['tracestate'],
        }
        
        try:
            if method.upper() == 'GET':
                resp = self.http_client.get(url, headers=headers)
            elif method.upper() == 'POST':
                resp = self.http_client.post(url, json=body, headers=headers)
            elif method.upper() == 'DELETE':
                resp = self.http_client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            data = resp.json() if resp.content else {}
            return data, resp.status_code
            
        except Exception as e:
            logger.error(f"SheerID request failed: {e}")
            return {'error': str(e)}, 500
    
    def _check_status(self) -> Dict:
        """Check current verification status."""
        data, status = self._sheerid_request(
            'GET',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}"
        )
        return {'status_code': status, 'data': data}
    
    def _submit_form(self, teacher_data: Dict, school: Dict) -> Dict:
        """Submit teacher verification form."""
        self._update_status("FORM", "📝 Submitting teacher info...")
        
        form_body = {
            'firstName': teacher_data['first_name'],
            'lastName': teacher_data['last_name'],
            'birthDate': teacher_data['birth_date'],
            'email': teacher_data['email'],
            'phoneNumber': '',
            'organization': {
                'id': school['id'],
                'idExtended': school['idExtended'],
                'name': school['name']
            },
            'deviceFingerprintHash': self.device_fingerprint,
            'locale': 'en-US',
            'metadata': {
                'marketConsentValue': False,
                'verificationId': self.verification_id,
            }
        }
        
        data, status = self._sheerid_request(
            'POST',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/collectTeacherPersonalInfo",
            form_body
        )
        
        if status == 404:
            raise Exception("Verification ID expired or invalid")
        if status != 200:
            raise Exception(f"Form submit failed: {data}")
        
        current_step = data.get('currentStep', 'unknown')
        
        if current_step == 'error':
            error_msg = data.get('errorMessage', 'Unknown')
            error_ids = data.get('errorIds', [])
            raise Exception(f"API Error: {error_msg} ({error_ids})")
        
        self._update_status("FORM", f"✅ Form submitted: step={current_step}")
        return data
    
    def _skip_sso(self) -> Dict:
        """Skip SSO step."""
        data, _ = self._sheerid_request(
            'DELETE',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/sso"
        )
        return data
    
    def _upload_document(self, teacher_data: Dict) -> Dict:
        """Generate and upload teacher document."""
        self._update_status("DOC", "🎨 Generating document...")
        
        # Generate document
        doc_data = TeacherDocumentData(
            first_name=teacher_data['first_name'],
            last_name=teacher_data['last_name'],
            employee_id=teacher_data.get('employee_id', '1234567'),
            department=teacher_data.get('department', 'General Education'),
            school_name=teacher_data['school_name'],
            hire_date=teacher_data.get('hire_date', '2020-08-15'),
            photo_path=None
        )
        
        template_name = get_random_school_template()
        image_bytes = generate_teacher_png(doc_data, template_name=template_name)
        
        self._update_status("DOC", "📤 Uploading document...")
        
        # Upload
        files = {'file': ('teacher_document.png', image_bytes, 'image/png')}
        
        headers = {
            'Accept': 'application/json',
            'Origin': SHEERID_BASE_URL,
        }
        
        resp = self.http_client.post(
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/docUpload",
            files=files,
            headers=headers
        )
        
        data = resp.json() if resp.content else {}
        
        if resp.status_code not in [200, 201]:
            raise Exception(f"Document upload failed: {data}")
        
        self._update_status("DOC", "✅ Document uploaded")
        return data
    
    def _handle_email_loop(self, teacher_data: Dict, school: Dict) -> Dict:
        """Handle emailLoop step using Mail.tm temporary email.
        
        Flow:
        1. Create temporary email via Mail.tm
        2. Submit email to SheerID (resend/request email verification)
        3. Poll Mail.tm inbox for SheerID email
        4. Extract verification token from email
        5. Submit token to SheerID to complete verification
        
        Returns:
            Dict with 'success', 'currentStep', etc.
        """
        self._update_status("EMAIL", "📧 Starting email verification via Mail.tm...")
        
        # Step 1: Create temporary email
        mail_client = MailTmClient(status_callback=self._update_status)
        email_address, _ = mail_client.create_account()
        
        if not email_address:
            mail_client.close()
            return {'success': False, 'message': 'Failed to create temporary email'}
        
        self._update_status("EMAIL", f"📧 Created: {email_address}")
        
        try:
            # Step 2: Submit email to SheerID
            self._update_status("EMAIL", "📤 Submitting email to SheerID...")
            
            # Update email in SheerID (set new email address for verification)
            submit_result = self._submit_email_for_loop(email_address)
            
            if not submit_result:
                return {'success': False, 'message': 'Failed to submit email to SheerID'}
            
            # Step 3: Wait for verification email
            self._update_status("EMAIL", "⏳ Waiting for SheerID verification email...")
            
            token = mail_client.wait_for_sheerid_email(
                verification_id=self.verification_id,
                max_wait=120,  # 2 minutes
                poll_interval=5
            )
            
            if not token:
                return {'success': False, 'message': 'Verification email not received'}
            
            self._update_status("TOKEN", f"🔑 Found token: {token}")
            
            # Step 4: Submit token to SheerID
            self._update_status("EMAIL", "📤 Submitting verification token...")
            
            verify_result = self._submit_email_token(token)
            
            if verify_result.get('currentStep') == 'success':
                self._update_status("SUCCESS", "✅ Email verified successfully!")
                return {
                    'success': True,
                    'currentStep': 'success',
                    'redirectUrl': verify_result.get('redirectUrl')
                }
            else:
                current_step = verify_result.get('currentStep', 'unknown')
                self._update_status("INFO", f"Next step: {current_step}")
                return {
                    'success': True,
                    'currentStep': current_step
                }
        
        except Exception as e:
            self._update_status("ERROR", f"Email loop failed: {str(e)}")
            return {'success': False, 'message': str(e)}
        
        finally:
            mail_client.close()
    
    def _submit_email_for_loop(self, email: str) -> bool:
        """Submit email address to SheerID for emailLoop verification.
        
        Args:
            email: The email address to verify
            
        Returns:
            True if successful
        """
        # Try to submit/update email address
        data, status = self._sheerid_request(
            'POST',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/emailLoop",
            body={'email': email}
        )
        
        if status in [200, 201]:
            return True
        
        # If that endpoint doesn't work, try resend email endpoint
        data, status = self._sheerid_request(
            'POST',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/resendEmail",
            body={'email': email}
        )
        
        return status in [200, 201]
    
    def _submit_email_token(self, token: str) -> Dict:
        """Submit email verification token to SheerID.
        
        Args:
            token: The email token extracted from verification email
            
        Returns:
            API response with currentStep, etc.
        """
        data, status = self._sheerid_request(
            'POST',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/emailLoop",
            body={'emailToken': token}
        )
        
        if status in [200, 201]:
            return data
        
        # Fallback: Try direct token submission
        data, status = self._sheerid_request(
            'POST',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/notifyEmail",
            body={'emailToken': token}
        )
        
        return data if status in [200, 201] else {}
    
    def _poll_for_result(self, max_checks: int = 20, interval: int = 15) -> Dict:
        """Poll for verification result."""
        self._update_status("POLL", "⏳ Waiting for verification result...")
        
        for i in range(max_checks):
            time.sleep(interval)
            
            status = self._check_status()
            data = status.get('data', {})
            current_step = data.get('currentStep', 'pending')
            
            self._update_status("POLL", f"Check {i+1}/{max_checks}: {current_step}")
            
            if current_step == 'success':
                redirect_url = data.get('redirectUrl', '')
                return {'approved': True, 'redirectUrl': redirect_url}
            
            if current_step == 'error':
                reasons = data.get('rejectionReasons', [])
                return {'approved': False, 'reasons': reasons}
            
            if current_step not in ['pending', 'docUpload', 'review']:
                break
        
        return {'approved': None, 'pending': True}
    
    def verify(self) -> Dict:
        """
        Run full verification flow.
        
        Returns:
            Dict with 'success', 'message', etc.
        """
        if not self.verification_id:
            raise ValueError("No verification ID")
        
        # Show IP
        flag = self._get_country_flag(self.ip_country)
        self._update_status("CONN", f"IP: {flag} {self.current_ip}")
        
        # Generate teacher
        district = random.choice(DISTRICT_TEMPLATES)
        teacher = generate_teacher_info(district=district)
        
        email = self.custom_email or teacher['email']
        school_id = teacher.get('school_id', DEFAULT_SCHOOL_ID) or DEFAULT_SCHOOL_ID
        school = SCHOOLS.get(str(school_id), SCHOOLS[DEFAULT_SCHOOL_ID])
        
        teacher_data = {
            'first_name': teacher['first_name'],
            'last_name': teacher['last_name'],
            'email': email,
            'birth_date': teacher['birth_date'],
            'school_name': teacher.get('school_name') or school['name'],
            'school_id': school_id,
            'position': teacher.get('position'),
            'hire_date': teacher.get('hire_date'),
            'department': teacher.get('department'),
            'employee_id': teacher.get('employee_id'),
        }
        
        self._update_status("INFO", f"👤 {teacher_data['first_name']} {teacher_data['last_name']}")
        self._update_status("INFO", f"🏫 {teacher_data['school_name']}")
        self._update_status("INFO", f"📧 {teacher_data['email']}")
        
        try:
            # Step 1: Check status
            status = self._check_status()
            current_step = status.get('data', {}).get('currentStep', 'unknown')
            self._update_status("STATUS", f"Current step: {current_step}")
            
            if current_step == 'success':
                self._update_status("SUCCESS", "✅ Already verified!")
                return {'success': True, 'message': 'Already verified'}
            
            if current_step == 'error':
                error_msg = status.get('data', {}).get('errorMessage', 'Unknown')
                raise Exception(f"Verification in error state: {error_msg}")
            
            # Step 2: Submit form
            if current_step == 'collectTeacherPersonalInfo':
                result = self._submit_form(teacher_data, school)
                current_step = result.get('currentStep', current_step)
            
            # Step 3: Skip SSO
            if current_step == 'sso':
                self._skip_sso()
                current_step = 'docUpload'
            
            # Step 4: Upload document
            if current_step == 'docUpload':
                result = self._upload_document(teacher_data)
                current_step = result.get('currentStep', 'pending')
            
            # Step 5: Handle emailLoop (using Mail.tm)
            if current_step == 'emailLoop':
                result = self._handle_email_loop(teacher_data, school)
                if result.get('success'):
                    current_step = result.get('currentStep', 'success')
                else:
                    raise Exception(result.get('message', 'Email verification failed'))
            
            # Step 5: Poll for result
            if current_step in ['pending', 'review']:
                poll_result = self._poll_for_result()
                
                if poll_result.get('approved') is True:
                    self._update_status("SUCCESS", "✅ VERIFICATION SUCCESSFUL!")
                    return {
                        'success': True,
                        'redirectUrl': poll_result.get('redirectUrl'),
                        'teacher': teacher_data
                    }
                elif poll_result.get('approved') is False:
                    reasons = poll_result.get('reasons', [])
                    self._update_status("FAIL", f"❌ Rejected: {reasons}")
                    return {'success': False, 'rejected': True, 'reasons': reasons}
                else:
                    self._update_status("PENDING", "⏳ Still pending review")
                    return {'success': False, 'pending': True}
            
            # Check final status
            if current_step == 'success':
                self._update_status("SUCCESS", "✅ VERIFICATION SUCCESSFUL!")
                return {'success': True, 'teacher': teacher_data}
            
            return {'success': False, 'message': f'Unexpected step: {current_step}'}
            
        except Exception as e:
            self._update_status("ERROR", f"❌ {str(e)}")
            return {'success': False, 'error': True, 'message': str(e)}
        
        finally:
            self.http_client.close()
