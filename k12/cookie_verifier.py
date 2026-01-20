"""K12 Cookie-Based Verifier - Uses User's Browser Session

Flow:
1. User opens SheerID in browser, completes captcha
2. User exports cookies (via extension like EditThisCookie)
3. User sends cookies JSON to bot: /verify2 -cookies "[{...}]"
4. Bot parses cookies, builds session, calls API
5. No session mismatch because using user's actual session!

Cookie format (EditThisCookie JSON export):
[
    {"name": "JSESSIONID", "value": "...", "domain": "services.sheerid.com", ...},
    {"name": "AWSALBCORS", "value": "...", ...},
    {"name": "sid-verificationId", "value": "...", ...}
]
"""
import json
import random
import logging
import time
import httpx
from typing import Dict, List, Optional
from http.cookiejar import CookieJar

# Import from local modules
try:
    from . import config
    from .name_generator import generate_teacher_info, PRIORITY_DISTRICTS, DISTRICT_PRIORITY_ORDER, mark_teacher_used
    from .img_generator import generate_teacher_png, TeacherDocumentData, get_random_school_template
except ImportError:
    import config
    from name_generator import generate_teacher_info, PRIORITY_DISTRICTS, DISTRICT_PRIORITY_ORDER, mark_teacher_used
    from img_generator import generate_teacher_png, TeacherDocumentData, get_random_school_template

# Import proxy manager
try:
    from config.proxy_manager import get_proxy_url, get_ip_display, get_proxy_manager
except ImportError:
    def get_proxy_url(): return None
    def get_ip_display(): return None
    def get_proxy_manager(): return None


# Priority district templates (use imported priority order)
DISTRICT_TEMPLATES = DISTRICT_PRIORITY_ORDER

# Config
PROGRAM_ID = config.PROGRAM_ID
SHEERID_BASE_URL = config.SHEERID_BASE_URL
SCHOOLS = config.SCHOOLS
DEFAULT_SCHOOL_ID = config.DEFAULT_SCHOOL_ID

# SheerID org search API (for K12 school verification)
SHEERID_ORG_SEARCH = "https://orgsearch.sheerid.net/rest/organization/search"

def search_k12_school(school_name: str) -> Dict:
    """Search for K12 school in SheerID database.
    
    Returns school info dict if found with type K12, else default school.
    """
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                SHEERID_ORG_SEARCH,
                params={
                    "accountId": "5e5297c2dfc5fb00012e0f21",  # OpenAI
                    "country": "US",
                    "type": "K12",
                    "name": school_name[:50]  # Limit query length
                }
            )
            
            if response.status_code == 200:
                schools = response.json()
                for school in schools:
                    if school.get("type") == "K12":
                        return {
                            "id": school.get("id"),
                            "idExtended": str(school.get("id")),
                            "name": school.get("name"),
                            "city": school.get("city") or "Unknown",
                            "state": school.get("state") or "US",
                            "country": "US",
                            "type": "K12"
                        }
    except Exception:
        pass
    
    # Fallback to default school
    return SCHOOLS[DEFAULT_SCHOOL_ID]

# Timing - Total wait: ~20 minutes
POLL_INTERVALS = [15, 15, 30, 30, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60]

# Document retry order when rejected - prioritize payslip (less fraud detection)
DOC_RETRY_ORDER = ["payslip", "id_card", "offer_letter"]
MAX_DOC_RETRIES = 3

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


def parse_cookie_json(cookie_json: str) -> Dict[str, str]:
    """
    Parse cookie JSON from browser extension (EditThisCookie format).
    
    Args:
        cookie_json: JSON string from extension export
        
    Returns:
        Dict of cookie name -> value
    """
    try:
        cookies_list = json.loads(cookie_json)
        
        # Convert list of cookie objects to simple dict
        cookies = {}
        for cookie in cookies_list:
            name = cookie.get('name')
            value = cookie.get('value')
            if name and value:
                cookies[name] = value
        
        return cookies
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid cookie JSON: {e}")


def extract_verification_id(cookies: Dict[str, str]) -> Optional[str]:
    """Extract verification ID from cookies."""
    return cookies.get('sid-verificationId')


class CookieVerifier:
    """Cookie-based SheerID K12 Teacher Verifier.
    
    Uses cookies exported from user's browser to maintain same session.
    No session mismatch = no "link expired" errors!
    """
    
    def __init__(self, cookies: Dict[str, str], custom_email: str = None, 
                 status_callback=None):
        """
        Args:
            cookies: Dict of cookie name -> value
            custom_email: Optional user email for SheerID confirmation
            status_callback: Optional callback(step, message) for real-time updates
        """
        self.cookies = cookies
        self.custom_email = custom_email
        self.verification_id = extract_verification_id(cookies)
        self.status_callback = status_callback
        
        # Get proxy from environment (Qv2ray default: socks5://host.docker.internal:10808)
        import os
        import socket
        proxy_url = os.environ.get('PROXY_URL', '')
        
        # Auto-detect proxy availability
        use_proxy = False
        if proxy_url:
            try:
                # Extract host:port from proxy URL
                # socks5://host.docker.internal:10808 -> host.docker.internal:10808
                proxy_parts = proxy_url.replace('socks5://', '').replace('http://', '').split(':')
                proxy_host = proxy_parts[0]
                proxy_port = int(proxy_parts[1]) if len(proxy_parts) > 1 else 10808
                
                # Test connection to proxy
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((proxy_host, proxy_port))
                sock.close()
                
                if result == 0:
                    use_proxy = True
                    logger.info(f"🌐 Proxy available: {proxy_url}")
                else:
                    logger.info(f"📡 Proxy not available, using direct connection")
            except Exception as e:
                logger.info(f"📡 Proxy check failed ({e}), using direct connection")
        
        # Build HTTP client with cookies and optional proxy
        client_kwargs = {
            'timeout': 60.0,
            'cookies': cookies,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': 'https://services.sheerid.com',
                'Referer': f'https://services.sheerid.com/verify/{PROGRAM_ID}/',
            }
        }
        
        # Add proxy if available and working
        if use_proxy:
            client_kwargs['proxy'] = proxy_url
        
        self.http_client = httpx.Client(**client_kwargs)
        
        # Store proxy status for display
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url if use_proxy else None
        
        # Get current IP address and country
        self.current_ip, self.ip_country = self._get_current_ip()
        
        self.device_fingerprint = self._generate_device_fingerprint()
    
    def _get_country_flag(self, country_code: str) -> str:
        """Convert country code to flag emoji (e.g., 'US' -> '🇺🇸')."""
        if not country_code or len(country_code) != 2:
            return "🌍"
        # Convert country code letters to regional indicator symbols
        return ''.join(chr(ord(c) + 127397) for c in country_code.upper())
    
    def _get_current_ip(self) -> tuple:
        """Get current public IP address and country to verify proxy is working."""
        try:
            # Use ip-api.com to get IP and country info
            response = self.http_client.get(
                "http://ip-api.com/json/?fields=query,countryCode",
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                ip = data.get('query', 'Unknown')
                country_code = data.get('countryCode', '')
                return ip, country_code
        except Exception as e:
            logger.warning(f"Failed to get IP: {e}")
        return "Unknown", ""
        
    def __del__(self):
        if hasattr(self, 'http_client'):
            self.http_client.close()
    
    # ============= COLOR SUPPORT =============
    # ANSI colors for terminal
    class Colors:
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BLUE = '\033[94m'
        MAGENTA = '\033[95m'
        RESET = '\033[0m'
        BOLD = '\033[1m'
    
    # Emoji for Telegram (no ANSI support)
    EMOJI = {
        'step': '🔵',
        'completed': '🟢',
        'success': '✅',
        'info': '📋',
        'warning': '⚠️',
        'error': '❌',
        'rejected': '🔴',
        'pending': '⏳',
        'upload': '📤',
    }
    
    def _update_status(self, step: str, message: str, msg_type: str = "info"):
        """
        Update status with colors for terminal and emoji for Telegram.
        
        msg_type: 'step', 'completed', 'success', 'info', 'warning', 'error', 'rejected'
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Terminal output with ANSI colors
        color_map = {
            'step': self.Colors.CYAN,
            'completed': self.Colors.GREEN,
            'success': self.Colors.GREEN,
            'info': self.Colors.YELLOW,
            'warning': self.Colors.YELLOW,
            'error': self.Colors.RED,
            'rejected': self.Colors.RED,
            'pending': self.Colors.MAGENTA,
        }
        color = color_map.get(msg_type, self.Colors.RESET)
        terminal_msg = f"[{timestamp}] {color}{message}{self.Colors.RESET}"
        print(terminal_msg)
        
        # Telegram callback with emoji (no ANSI)
        if self.status_callback:
            emoji = self.EMOJI.get(msg_type, '')
            telegram_msg = f"[{timestamp}] {emoji} {message}" if emoji else f"[{timestamp}] {message}"
            try:
                self.status_callback(step, telegram_msg)
            except Exception as e:
                logger.error(f"Status callback error: {e}")
    
    def _log_step(self, step_num: int, message: str, completed: bool = False, status: str = None):
        """Log step progress in Step X/7 format with colors."""
        total_steps = 7
        if completed:
            msg = f"Step {step_num} completed: {status or 'OK'}"
            self._update_status(f"STEP{step_num}", msg, "completed")
        else:
            msg = f"Step {step_num}/{total_steps}: {message}"
            self._update_status(f"STEP{step_num}", msg, "step")

    def _log_info(self, label: str, value: str):
        """Log info line with yellow color."""
        self._update_status("INFO", f"{label}: {value}", "info")
    
    @staticmethod
    def _generate_device_fingerprint() -> str:
        chars = '0123456789abcdef'
        return ''.join(random.choice(chars) for _ in range(32))
    
    def _human_delay(self, min_sec: float = 0.5, max_sec: float = 2.0):
        """Add random human-like delay between requests."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def _sheerid_request(self, method: str, url: str, body: Optional[Dict] = None) -> tuple:
        """Make request to SheerID API using session cookies with anti-bot measures."""
        
        # Add random delay before request (human-like behavior)
        self._human_delay(0.3, 1.5)
        
        # Realistic Chrome headers
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        
        try:
            response = self.http_client.request(
                method=method, url=url, json=body, headers=headers
            )
            try:
                data = response.json()
            except Exception:
                data = {"raw": response.text}
            return data, response.status_code
        except Exception as e:
            logger.error(f"SheerID request failed: {e}")
            raise
    
    def _upload_to_s3(self, upload_url: str, content: bytes, mime_type: str) -> bool:
        """Upload document to S3."""
        try:
            headers = {'Content-Type': mime_type}
            response = self.http_client.put(
                upload_url, content=content, headers=headers, timeout=60.0
            )
            return 200 <= response.status_code < 300
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False
    
    def check_status(self) -> Dict:
        """Check current verification status."""
        data, status = self._sheerid_request(
            'GET',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}"
        )
        
        # Log raw response for debugging
        current_step = data.get('currentStep', 'unknown')
        if current_step in ('error', 'unknown') or status != 200:
            logger.error(f"SheerID API Error - Status: {status}, Response: {data}")
        
        return {
            'current_step': current_step,
            'redirect_url': data.get('redirectUrl'),
            'status_code': status,
            'data': data,
            'raw_response': str(data)[:500]  # Truncated for display
        }
    
    def _refresh_verification_id(self) -> bool:
        """Attempt to get a new Verification ID by visiting the landing page."""
        try:
            self._update_status("REFRESH", "🔄 Refreshing session for new Verification ID...")
            
            # Request landing page to get new ID
            response = self.http_client.get(
                f"{SHEERID_BASE_URL}/verify/{PROGRAM_ID}/",
                follow_redirects=True
            )
            
            # Debug: Log Refresh Response
            self._update_status("DEBUG", f"Refresh Status: {response.status_code}")
            
            # Check cookies for new verificationId
            # httpx uses .items() for cookie iteration
            for cookie_name, cookie_value in response.cookies.items():
                if cookie_name == 'sid-verificationId':
                    new_id = cookie_value
                    if new_id != self.verification_id:
                        self.verification_id = new_id
                        self._update_status("REFRESH", f"✅ Got new ID: {new_id[:20]}...")
                        return True
                    else:
                        self._update_status("DEBUG", "⚠️ Got same ID (No refresh)")
            
            # If loop finishes without returning
            self._update_status("DEBUG", f"Cookies received: {list(response.cookies.keys())}")
            self._update_status("ERROR", "❌ Could not get new Verification ID")
            return False
        except Exception as e:
            logger.error(f"Refresh failed: {e}")
            self._update_status("ERROR", f"❌ Refresh exception: {e}")
            return False
    
    def _submit_form(self, teacher_data: Dict, school: Dict) -> Dict:
        """Submit teacher verification form."""
        self._update_status("STEP1", "📝 POST /collectTeacherPersonalInfo...")
        
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
                'refererUrl': f"{SHEERID_BASE_URL}/verify/{PROGRAM_ID}/?verificationId={self.verification_id}",
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
        
        # Check specific error step
        current_step = data.get('currentStep', 'unknown')
        
        if current_step == 'error':
            error_ids = data.get('errorIds', [])
            error_msg = data.get('errorMessage') or data.get('systemErrorMessage', 'Unknown API Error')
            
            # Check for invalidStep - link in wrong state (per tutorial)
            if 'invalidStep' in error_ids:
                self._update_status("ERROR", "❌ Link không ở trạng thái form. Cần tạo link mới!")
                self._update_status("ERROR", "💡 Hãy upload ảnh trắng/đen vào SheerID để link hết hạn, sau đó gửi link mới.")
                raise Exception(f"Invalid link state: {error_msg}")
            
            self._update_status("ERROR", f"❌ API Error: {error_msg}")
            # Raise exception to trigger retry
            raise Exception(f"API Error: {error_msg}")

        # Show real response data
        estimated_time = data.get('estimatedReviewTime', 'N/A')
        max_time = data.get('maxReviewTime', 'N/A')
        
        self._update_status("STEP1", f"✅ Response: currentStep={current_step}")
        self._update_status("STEP1", f"⏱️ estimatedReviewTime: {estimated_time}")
        
        return data
    
    def _skip_sso(self) -> Dict:
        """Skip SSO step."""
        logger.info("⏭️ Skipping SSO...")
        data, _ = self._sheerid_request(
            'DELETE',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/sso"
        )
        return data
    
    def _upload_document(self, teacher_data: Dict, doc_type: str = "id_card") -> Dict:
        """Generate and upload teacher document."""
        from pathlib import Path
        from datetime import datetime
        
        logger.info(f"📄 Generating {doc_type} document...")
        
        # Get district template from teacher data (ensures consistency)
        district_template = teacher_data.get('district_template', 'nyc_doe')
        
        # Create shared data for consistent documents - USE ALL ENRICHED FIELDS
        if not hasattr(self, '_shared_doc_data'):
            self._shared_doc_data = TeacherDocumentData(
                teacher_data['first_name'], 
                teacher_data['last_name'],
                school_name=teacher_data.get('school_name'),
                school_template=district_template,  # Use matching template!
                position=teacher_data.get('position'),  # Teacher's actual position
                hire_date=teacher_data.get('hire_date'),  # Teacher's actual hire date
                employee_id=teacher_data.get('employee_id'),  # Consistent employee ID!
                annual_salary=teacher_data.get('annual_salary'),  # Matching salary
                salary_step=teacher_data.get('salary_step'),  # Salary step level
                department=teacher_data.get('department'),  # Matching department
                pension_number=teacher_data.get('pension_number'),  # Pension number
            )
            
            # Create document_review folder with timestamp
            review_dir = Path(__file__).parent / "document_review" / datetime.now().strftime("%Y%m%d_%H%M%S")
            review_dir.mkdir(parents=True, exist_ok=True)
            self._review_dir = review_dir
            
            # Save teacher info JSON for debugging
            teacher_info = {
                "full_name": self._shared_doc_data.full_name,
                "employee_id": self._shared_doc_data.employee_id_formatted,
                "school_name": self._shared_doc_data.school_name,
                "district": self._shared_doc_data.district_name,
                "salary": self._shared_doc_data.salary_formatted,
                "position": self._shared_doc_data.position,
                "hire_date": self._shared_doc_data.hire_date,
                "school_template": self._shared_doc_data.school_template,
                "district_template": district_template,
                "submitted_data": teacher_data
            }
            info_path = review_dir / "teacher_info.json"
            info_path.write_text(json.dumps(teacher_info, indent=2, ensure_ascii=False))
            logger.info(f"📝 Saved teacher info: {info_path} (Template: {district_template})")
        
        # Generate document with shared data and correct template
        png_data = generate_teacher_png(
            teacher_data['first_name'], 
            teacher_data['last_name'], 
            teacher_data['school_name'],
            doc_type=doc_type,
            shared_data=self._shared_doc_data,
            school_template=district_template  # Ensure correct template
        )
        png_size = len(png_data)
        self._update_status("STEP2", f"Document: {png_size/1024:.1f}KB ({doc_type})", "success")
        
        # Save to document_review folder
        if hasattr(self, '_review_dir'):
            doc_path = self._review_dir / f"{doc_type}.png"
            doc_path.write_bytes(png_data)
        
        # Store document for later retrieval (send to Telegram)
        self.last_document_bytes = png_data
        
        # === STEP 4/7: Request upload URL ===
        self._log_step(4, "Requesting document upload URL ...")
        doc_body = {
            'files': [{
                'fileName': 'teacher_verification.png',
                'mimeType': 'image/png',
                'fileSize': png_size
            }]
        }
        doc_data, doc_status = self._sheerid_request(
            'POST',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/docUpload",
            doc_body
        )
        
        if doc_status != 200:
            raise Exception(f"docUpload failed: {doc_data}")
        
        documents = doc_data.get('documents') or []
        if not documents:
            raise Exception(f"No upload URL: {doc_data}")
        
        self._update_status("INFO", "Upload URL obtained", "success")
        upload_url = documents[0]['uploadUrl']
        # Show truncated URL
        url_short = upload_url[:60] + "..." if len(upload_url) > 60 else upload_url
        self._update_status("INFO", f"Upload URL: {url_short}", "info")
        
        # === STEP 5/7: Upload to S3 ===
        self._log_step(5, "Uploading teacher document image to S3 ...")
        if not self._upload_to_s3(upload_url, png_data, 'image/png'):
            raise Exception("S3 upload failed")
        self._update_status("SUCCESS", "Teacher document uploaded successfully", "success")
        
        # === STEP 6/7: Complete upload ===
        self._log_step(6, "Completing document upload ...")
        complete_data, _ = self._sheerid_request(
            'POST',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/completeDocUpload"
        )
        
        current_step = complete_data.get('currentStep', 'unknown')
        self._log_step(6, "", completed=True, status=current_step)
        
        return complete_data
    
    def _poll_for_result(self) -> Dict:
        """
        Poll for verification result.
        NO RETRY on document rejection - Fail fast to try new teacher.
        """
        # === STEP 7/7: Checking verification status ===
        self._log_step(7, "Checking verification status ...")
        
        MAX_WAIT_SECONDS = 45 * 60
        POLL_INTERVAL = 30
        MAX_CHECKS = 10
        
        total_time = 0
        check_count = 0
        error_streak = 0  # Count consecutive errors
        
        while total_time < MAX_WAIT_SECONDS and check_count < MAX_CHECKS:
            time.sleep(POLL_INTERVAL)
            total_time += POLL_INTERVAL
            check_count += 1
            
            try:
                status = self.check_status()
                current_step = status['current_step']
                status_code = status.get('status_code')
                data = status.get('data', {})
                
                # Reset error streak on valid response
                if status_code == 200 and current_step not in ('error', 'unknown'):
                    error_streak = 0
                
                # Status check counter like screenshot
                self._update_status("POLL", f"Status check {check_count}/{MAX_CHECKS}: {current_step}", "pending")
                
                # SUCCESS
                if current_step == 'success':
                    self._update_status("SUCCESS", "Document submitted successfully, pending review", "success")
                    return {'approved': True, 'status': status}
                
                # REJECTED - Try blank image trick first (per tutorial)
                if current_step == 'rejected':
                    reasons = data.get('rejectionReasons', [])
                    reason_text = ', '.join(reasons) if reasons else 'Unknown'
                    self._update_status("REJECTED", f"Document rejected: {reason_text}", "rejected")
                    
                    # Blank image trick: Upload blank images to trigger link expiration
                    self._update_status("INFO", "🔄 Trying blank image trick to expire link...")
                    for blank_i in range(3):
                        try:
                            self._update_status("INFO", f"📄 Blank image {blank_i+1}/3...")
                            self._upload_document(self.last_teacher_data or {}, doc_type="blank")
                            time.sleep(3)
                        except Exception as e:
                            self._update_status("WARN", f"Blank upload {blank_i+1}: {str(e)[:50]}")
                    
                    return {'approved': False, 'rejected': True, 'rejection_reasons': reasons}
                
                # docUpload loop (soft rejection)
                if current_step == 'docUpload' and total_time > 60:
                     reasons = data.get('rejectionReasons', [])
                     if reasons:
                         reason_text = ', '.join(reasons)
                         self._update_status("REJECTED", f"Re-upload required: {reason_text}", "rejected")
                         return {'approved': False, 'rejected': True, 'rejection_reasons': reasons}
                
                # Pending status - document under review
                if current_step == 'pending':
                    if check_count >= MAX_CHECKS:
                        self._update_status("INFO", "Document submitted successfully, pending review", "success")
                        self._update_status("INFO", "Document has been submitted and is under review", "pending")
                        return {'approved': None, 'pending': True, 'status': status}
                
                # Error Handling with Streak
                if current_step == 'error' or status_code != 200:
                    error_streak += 1
                    msg = (
                        data.get('errorMessage') or 
                        data.get('message') or 
                        data.get('errorCode') or 
                        str(data)[:100]
                    )
                    
                    if error_streak < 3:
                        self._update_status("WARN", f"API Error ({error_streak}/3): {msg}. Retrying...", "warning")
                        continue
                    else:
                        self._update_status("ERROR", f"Persistent API Error: {msg}", "error")
                        return {'approved': False, 'error': True, 'message': msg}
                    
            except Exception as e:
                error_streak += 1
                if error_streak < 3:
                     self._update_status("WARN", f"Check failed ({error_streak}/3): {str(e)[:50]}")
                     continue
                else:
                    msg = f"Persistent Exception: {str(e)}"
                    self._update_status("ERROR", msg)
                    return {'approved': False, 'error': True, 'message': msg}
        
        # Max checks reached - likely still pending
        self._update_status("INFO", "Document submitted successfully, pending review")
        self._update_status("INFO", "Document has been submitted and is under review")
        return {'approved': None, 'pending': True}
    
    def verify(self, fast_mode: bool = False) -> Dict:
        """
        Run verification flow with up to 3 ATTEMPTS (New Teacher Profiles).
        
        Args:
            fast_mode: If True, skip document upload and retry with new teacher if doc required.
        """
        if not self.verification_id:
            raise ValueError("Không tìm thấy verification ID trong cookies")
        
        # Connection Info - only show when proxy is enabled
        ip_display = get_ip_display()
        if ip_display:
            self._update_status("CONN", f"IP: {ip_display}")
        # else: no proxy, don't show IP info
        
        MAX_ATTEMPTS = 3
        mode_text = "⚡ FAST MODE" if fast_mode else "📄 NORMAL MODE"
        self._update_status("MODE", mode_text)
        
        # Track last error for final message
        last_error = "Unknown"
        last_step = "Unknown"
        
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._update_status("ATTEMPT", f"\n🎯 ━━━━━━━━ THỬ LẦN {attempt}/{MAX_ATTEMPTS} ━━━━━━━━")
            
            # 1. Select district template based on attempt (priority order)
            # Attempt 1 -> nyc_doe, Attempt 2 -> miami_dade, Attempt 3 -> springfield_high
            district_template = DISTRICT_TEMPLATES[(attempt - 1) % len(DISTRICT_TEMPLATES)]
            teacher = generate_teacher_info(district=district_template)
            
            email = self.custom_email if self.custom_email else teacher['email']
            
            # Dynamic K12 school lookup from SheerID (fixes school ID mismatch)
            teacher_school_name = teacher.get('school_name', '')
            school = search_k12_school(teacher_school_name) if teacher_school_name else SCHOOLS[DEFAULT_SCHOOL_ID]
            school_id = school.get('id', DEFAULT_SCHOOL_ID)
            
            teacher_data = {
                # Basic info
                'first_name': teacher['first_name'], 
                'last_name': teacher['last_name'],
                'email': email,
                'birth_date': teacher['birth_date'],
                
                # School
                'school_name': teacher.get('school_name') or school['name'],
                'school_id': school_id,
                'district_template': district_template,  # Track which template to use
                
                # Position & Employment
                'position': teacher.get('position'),
                'hire_date': teacher.get('hire_date'),
                'department': teacher.get('department'),
                
                # Enriched data for document consistency
                'employee_id': teacher.get('employee_id'),
                'employee_id_formatted': teacher.get('employee_id_formatted'),
                'annual_salary': teacher.get('annual_salary'),
                'salary_step': teacher.get('salary_step'),
                'pension_number': teacher.get('pension_number'),
            }
            
            # Log Info
            self._update_status("INFO", "DATA: ✅ Using Real Scraped Data")
            self._update_status("INFO", f"👤 Profile: {teacher_data['first_name']} {teacher_data['last_name']}")
            self._update_status("INFO", f"🏫 School: {teacher_data['school_name']}")
            self._update_status("VID", f"🔑 ID: {self.verification_id[-10:]}")
            
            try:
                # 2. Run Flow: Status Check -> Form -> SSO -> (Upload if not fast) -> Poll
                result = self._run_single_attempt(teacher_data, school, fast_mode=fast_mode)
                
                # Fast mode: if doc required, retry with new teacher
                if fast_mode and result.get('needs_doc'):
                    last_error = "Document required (Fast mode skipped)"
                    last_step = "Step 2: Doc Upload"
                    self._update_status("SKIP", "⚡ Fast mode: Cần doc, thử teacher khác...")
                    # Fall through to refresh logic below
                
                elif result.get('success'):
                    self._update_status("SUCCESS", f"VERIFY THANH CONG (Lan {attempt})")
                    # Mark teacher as used to avoid repeat
                    mark_teacher_used(teacher_data.get('email', ''))
                    return result
                
                elif result.get('rejected'):
                    reasons = result.get('rejection_reasons', [])
                    last_error = f"Rejected: {', '.join(reasons) if reasons else 'Unknown'}"
                    last_step = "Step 3: Poll Result"
                    self._update_status("FAIL", f"❌ Attempt {attempt} thất bại: {last_error}")
                
                elif result.get('error'):
                    last_error = result.get('message', 'API Error')
                    last_step = "API Call"
                    self._update_status("FAIL", f"❌ Attempt {attempt} lỗi API: {last_error}")
                
                else:
                    last_error = str(result)[:100]
                    last_step = "Unknown"
                    self._update_status("FAIL", f"❌ Attempt {attempt} result unknown: {last_error}")
                
                # If failed and have attempts left -> Refresh ID
                if attempt < MAX_ATTEMPTS:
                    self._update_status("NEXT", "⚠️ Thất bại, đang thử profile mới...")
                    
                    # Anti-detection: Random wait and new fingerprint
                    wait_time = random.uniform(5, 8)
                    self._update_status("WAIT", f"⏳ Waiting {wait_time:.1f}s (anti-detect)...")
                    time.sleep(wait_time)
                    
                    self.device_fingerprint = self._generate_device_fingerprint()
                    
                    if self._refresh_verification_id():
                         # Clean up previous attempt data
                        self.last_document_bytes = None
                        self.last_teacher_data = None
                        # Reset shared doc data for new teacher
                        if hasattr(self, '_shared_doc_data'):
                            delattr(self, '_shared_doc_data')
                        continue
                    else:
                        last_error = "Cannot refresh Verification ID"
                        last_step = "Session Refresh"
                        self._update_status("STOP", "❌ Không thể lấy Verification ID mới. Dừng lại.")
                        break
                
            except Exception as e:
                last_error = str(e)
                last_step = "Exception"
                self._update_status("ERROR", f"❌ Lỗi lần {attempt}: {e}")
                if attempt < MAX_ATTEMPTS:
                    # Anti-detection delay
                    wait_time = random.uniform(5, 8)
                    self._update_status("WAIT", f"⏳ Waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    self.device_fingerprint = self._generate_device_fingerprint()
                    
                    if self._refresh_verification_id():
                        continue
        
        # Final failure message with details
        self._update_status("FINAL", f"━━━ KẾT QUẢ CUỐI CÙNG ━━━")
        self._update_status("FINAL", f"❌ Thất bại sau {MAX_ATTEMPTS} lần thử")
        self._update_status("FINAL", f"📍 Step cuối: {last_step}")
        self._update_status("FINAL", f"💬 Lý do: {last_error}")
        
        return {'success': False, 'message': f'All attempts failed. Last: {last_step} - {last_error}'}

    def _run_single_attempt(self, teacher_data: Dict, school: Dict, fast_mode: bool = False) -> Dict:
        """Execute one full verification pass for a specific teacher profile.
        
        Args:
            teacher_data: Teacher information dict
            school: School information dict
            fast_mode: If True, skip document upload step
        """
        
        teacher_info = {
            'name': f"{teacher_data['first_name']} {teacher_data['last_name']}",
            'email': teacher_data['email'],
            'birth_date': teacher_data['birth_date'],
            'school': school['name'],
        }

        # Store for potential usage (though we disabled doc retry)
        self.last_teacher_data = teacher_data
        
        # === STEP 1/7: Init Info ===
        self._log_info("Verification ID", self.verification_id)
        self._log_info("Device fingerprint", self.device_fingerprint)
        
        # Check status
        status = self.check_status()
        current_step = status.get('current_step')
        status_code = status.get('status_code')
        
        # Handle initial errors
        if status_code != 200:
             raise Exception(f"Initial status check failed: {status_code}")

        # Check if already succeeded (e.g., from previous session)
        if current_step == 'success':
            self._update_status("SUCCESS", "Already verified!")
            return {'success': True, 'redirect_url': status.get('data', {}).get('redirectUrl'), 'teacher_info': teacher_info}
        
        # Check if in error state from previous attempt
        if current_step == 'error':
            error_msg = status.get('data', {}).get('errorMessage', 'Previous error state')
            raise Exception(f"Verification in error state: {error_msg}")

        # === STEP 2/7: Submit Form ===
        if current_step == 'collectTeacherPersonalInfo':
            self._log_step(2, "Submitting teacher information ...")
            time.sleep(random.uniform(2, 4))
            res = self._submit_form(teacher_data, school)
            current_step = res.get('currentStep')
            self._log_step(2, "", completed=True, status=current_step)
        
        # === STEP 3/7: Skip SSO ===
        if current_step == 'sso':
            self._log_step(3, "Skipping SSO verification ...")
            self._skip_sso()
            current_step = 'docUpload'
            self._log_step(3, "", completed=True, status=current_step)
            
        if current_step == 'success':
            return {'success': True, 'redirect_url': status.get('redirectUrl'), 'teacher_info': teacher_info}

        # === STEP 4-6/7: Document Upload ===
        doc_bytes = None
        if current_step == 'docUpload':
            if fast_mode:
                # Fast mode: Don't upload, signal caller to retry with new teacher
                self._update_status("FAST", "Doc required - Fast mode skipping")
                return {'success': False, 'needs_doc': True, 'teacher_info': teacher_info}
            
            # Use payslip as primary - less fraud detection than ID card
            self._upload_document(teacher_data, doc_type="payslip")
            doc_bytes = getattr(self, 'last_document_bytes', None)
        
        # === STEP 7/7: Poll for Result ===
        poll_result = self._poll_for_result()
        
        if poll_result.get('approved'):
            return {
                'success': True,
                'redirect_url': poll_result['status'].get('redirect_url'),
                'teacher_info': teacher_info,
                'document_bytes': doc_bytes
            }
            
        # Include rejection reasons from poll if available
        rejection_reasons = poll_result.get('rejection_reasons', [])
        return {'success': False, 'rejected': True, 'rejection_reasons': rejection_reasons}


def verify_with_cookies(cookie_json: str, custom_email: str = None, 
                        status_callback=None, fast_mode: bool = False) -> Dict:
    """
    Convenience function to run cookie-based verification.
    
    Args:
        cookie_json: JSON string from browser extension (EditThisCookie format)
        custom_email: Optional user email
        status_callback: Optional callback(step, message) for real-time updates
        fast_mode: If True, skip document upload and retry with new teacher if doc required
        
    Returns:
        Verification result dict
    """
    cookies = parse_cookie_json(cookie_json)
    verifier = CookieVerifier(cookies, custom_email=custom_email, 
                              status_callback=status_callback)
    return verifier.verify(fast_mode=fast_mode)


if __name__ == "__main__":
    # Test with sample cookie JSON
    test_cookies = '''[
        {"name": "JSESSIONID", "value": "test_session", "domain": "services.sheerid.com"},
        {"name": "sid-verificationId", "value": "test_verification_id", "domain": "services.sheerid.com"}
    ]'''
    
    print("Testing Cookie Parser...")
    cookies = parse_cookie_json(test_cookies)
    print(f"Parsed cookies: {cookies}")
    print(f"Verification ID: {extract_verification_id(cookies)}")
