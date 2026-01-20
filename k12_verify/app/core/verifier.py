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
import base64
import httpx
from typing import Dict, List, Optional
from http.cookiejar import CookieJar

# Cloudscraper for Cloudflare bypass (ported from military module)
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

# Import from local modules
try:
    from .. import config as app_config
    from . import config
    from .name_generator import generate_teacher_info, PRIORITY_DISTRICTS
    from .document_gen import generate_teacher_png, TeacherDocumentData, get_random_school_template
except ImportError:
    from app import config as app_config
    from app.core import config
    from app.core.name_generator import generate_teacher_info, PRIORITY_DISTRICTS
    from app.core.document_gen import generate_teacher_png, TeacherDocumentData, get_random_school_template

# Use districts from app config (avoid duplication)
DISTRICT_TEMPLATES = list(app_config.DISTRICTS.keys())

# Config
PROGRAM_ID = config.PROGRAM_ID
SHEERID_BASE_URL = config.SHEERID_BASE_URL
SCHOOLS = config.SCHOOLS
DEFAULT_SCHOOL_ID = config.DEFAULT_SCHOOL_ID

# Timing - Total wait: ~20 minutes
POLL_INTERVALS = [15, 15, 30, 30, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60]

# Document retry order when rejected - prioritize payslip (less fraud detection)
DOC_RETRY_ORDER = ["payslip", "id_card", "offer_letter"]
MAX_DOC_RETRIES = 3

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


# ============= ANTI-DETECTION: NewRelic Headers (from military module) =============
def generate_newrelic_headers() -> Dict[str, str]:
    """
    Generate NewRelic tracking headers to mimic real browser telemetry.
    Ported from military/api_verifier.py for anti-bot bypass.
    """
    trace_id = ''.join(random.choices('0123456789abcdef', k=32))
    span_id = ''.join(random.choices('0123456789abcdef', k=16))
    
    nr_data = {
        "v": [0, 1],
        "d": {
            "ty": "Browser",
            "ac": "3962051",
            "ap": "1480827621",
            "id": span_id[:16],
            "tr": trace_id,
            "ti": int(time.time() * 1000)
        }
    }
    
    return {
        "newrelic": base64.b64encode(json.dumps(nr_data).encode()).decode(),
        "traceparent": f"00-{trace_id}-{span_id}-01",
        "tracestate": f"3962051@nr=0-1-3962051-1480827621-{span_id}----{int(time.time() * 1000)}"
    }


# ============= ERROR CATEGORIZATION (from military module) =============
ERROR_ACTIONS = {
    "notApproved": {"action": "change_ip", "message": "Not approved - try different IP"},
    "limitExceeded": {"action": "change_profile", "message": "Profile overused - try different teacher"},
    "invalidPersonInfo": {"action": "change_profile", "message": "Invalid info - try different teacher"},
    "invalidBirthDate": {"action": "change_profile", "message": "Invalid birth date"},
    "verificationLimitExceeded": {"action": "wait", "message": "Rate limited - wait and retry"},
    "maxRetriesReached": {"action": "wait", "message": "Max retries - wait 24h"},
    "fraudSuspected": {"action": "change_ip", "message": "Fraud detected - rotate IP"},
    "docUploadRejected": {"action": "change_doc", "message": "Document rejected - try different type"},
}


def categorize_error(error_ids: list) -> Dict:
    """Categorize error and suggest action."""
    for error_id in error_ids:
        if error_id in ERROR_ACTIONS:
            return ERROR_ACTIONS[error_id]
    return {"action": "unknown", "message": "Unknown error"}


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
        
        # Get proxy from config (supports DataImpulse sticky session)
        import os
        import socket
        from dotenv import load_dotenv
        
        # Force reload .env to get latest values
        load_dotenv(override=True)
        
        # Build proxy URL from env vars
        proxy_enabled = os.getenv('PROXY_ENABLED', 'false').lower() == 'true'
        proxy_url = None
        use_proxy = False
        
        if proxy_enabled:
            proxy_host = os.getenv('PROXY_HOST', '')
            proxy_port = os.getenv('PROXY_PORT', '10000')
            proxy_user = os.getenv('PROXY_USER', '')
            proxy_pass = os.getenv('PROXY_PASS', '')
            
            if proxy_user and proxy_pass and proxy_host:
                proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
                
                # Test connection to proxy
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((proxy_host, int(proxy_port)))
                    sock.close()
                    
                    if result == 0:
                        use_proxy = True
                        logger.info(f"[PROXY MODE] Connected: {proxy_host}:{proxy_port}")
                    else:
                        logger.warning(f"[PROXY] Connection failed (code {result}), using direct")
                except Exception as e:
                    logger.warning(f"[PROXY] Check failed ({e}), using direct")
        else:
            # VPN Mode: Using external VPN or direct connection
            logger.info("[VPN/DIRECT MODE] Proxy disabled, using system network")
        
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
        
        # Safe print for Windows (handle Unicode errors)
        try:
            print(terminal_msg)
        except UnicodeEncodeError:
            # Fallback: remove emojis for Windows console
            safe_msg = terminal_msg.encode('ascii', 'replace').decode('ascii')
            print(safe_msg)
        
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
    
    # Pool of realistic User-Agents for rotation
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    ]
    
    # Screen resolutions for fingerprint
    SCREEN_RESOLUTIONS = [
        (1920, 1080), (1366, 768), (1536, 864), (1440, 900), 
        (1280, 720), (2560, 1440), (1680, 1050), (1600, 900)
    ]
    
    # Timezones (US)
    TIMEZONES = [
        'America/New_York', 'America/Chicago', 'America/Denver', 
        'America/Los_Angeles', 'America/Phoenix'
    ]
    
    def _get_random_browser_config(self) -> dict:
        """Generate random browser fingerprint config."""
        ua = random.choice(self.USER_AGENTS)
        screen = random.choice(self.SCREEN_RESOLUTIONS)
        tz = random.choice(self.TIMEZONES)
        
        # Determine browser type from UA
        if 'Firefox' in ua:
            sec_ch_ua = '"Firefox";v="121"'
        elif 'Edg' in ua:
            sec_ch_ua = '"Microsoft Edge";v="120", "Chromium";v="120"'
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
    
    def _update_env_session(self, new_session: str):
        """Update PROXY_SESSION in .env file."""
        from pathlib import Path
        import re
        
        env_path = Path(__file__).parent.parent.parent / ".env"
        
        if not env_path.exists():
            self._update_status("DEBUG", f".env not found at {env_path}")
            return
        
        try:
            content = env_path.read_text(encoding='utf-8')
            
            # Replace PROXY_SESSION line
            if 'PROXY_SESSION=' in content:
                content = re.sub(
                    r'PROXY_SESSION=.*',
                    f'PROXY_SESSION={new_session}',
                    content
                )
            else:
                # Add if not exists
                content += f'\nPROXY_SESSION={new_session}\n'
            
            env_path.write_text(content, encoding='utf-8')
            self._update_status("PROXY", f"📝 Updated .env: PROXY_SESSION={new_session}")
            self._update_status("WARNING", f"⚠️ Update SwitchyOmega: __sess.{new_session}")
        except Exception as e:
            self._update_status("DEBUG", f"Failed to update .env: {e}")
    
    def _rotate_proxy_session(self):
        """
        Auto-rotate proxy session to get new IP when fraud detected.
        Generates new session ID and rebuilds HTTP client with new proxy URL.
        """
        import os
        from dotenv import load_dotenv
        import uuid
        
        load_dotenv(override=True)
        proxy_enabled = os.getenv('PROXY_ENABLED', 'false').lower() == 'true'
        
        if not proxy_enabled:
            self._update_status("INFO", "[VPN MODE] Session rotation skipped (using external VPN)")
            return
        
        # Generate new random session ID (12 chars to avoid collision)
        new_session = f"sess_{uuid.uuid4().hex[:12]}"
        self._update_status("PROXY", f"🔄 New session: {new_session}")
        
        # Update .env file with new session
        self._update_env_session(new_session)
        
        # Rebuild proxy URL with new session
        proxy_host = os.getenv('PROXY_HOST', '')
        proxy_port = os.getenv('PROXY_PORT', '10000')
        proxy_user = os.getenv('PROXY_USER', '')
        proxy_pass = os.getenv('PROXY_PASS', '')
        
        if proxy_user and proxy_pass and proxy_host:
            # DataImpulse format with session
            username = f"{proxy_user}__sess.{new_session}"
            new_proxy_url = f"http://{username}:{proxy_pass}@{proxy_host}:{proxy_port}"
            
            # Rebuild HTTP client with new proxy
            import httpx
            self.http_client.close()
            self.http_client = httpx.Client(
                timeout=60.0,
                cookies=self.cookies,
                proxy=new_proxy_url,
                headers={
                    'User-Agent': random.choice(self.USER_AGENTS),
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            )
            
            # Get new IP to confirm rotation
            new_ip, new_country = self._get_current_ip()
            flag = self._get_country_flag(new_country)
            
            if new_ip == self.current_ip:
                self._update_status("WARNING", f"⚠️ Proxy IP không đổi ({new_ip}). Thử lại lần nữa...")
            else:
                self._update_status("PROXY", f"New IP: {flag} {new_ip}")
            
            self.current_ip = new_ip
            self.ip_country = new_country
    
    def _human_delay(self, min_sec: float = 2.0, max_sec: float = 5.0):
        """Add random human-like delay between requests (increased for anti-detection)."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def _sheerid_request(self, method: str, url: str, body: Optional[Dict] = None) -> tuple:
        """Make request to SheerID API using session cookies with anti-bot measures.
        
        Enhanced with techniques from military module:
        - NewRelic tracking headers (mimic real browser telemetry)
        - SheerID client version headers
        - Increased human-like delays
        """
        
        # Add human-like delay before request (increased from 0.3-1.5s to 2-5s)
        self._human_delay(2.0, 5.0)
        
        # Get random browser config for this request
        browser_config = self._get_random_browser_config()
        
        # Generate NewRelic headers for anti-bot bypass (from military module)
        nr_headers = generate_newrelic_headers()
        
        # Dynamic headers based on random browser config + NewRelic + SheerID client info
        headers = {
            # Standard headers
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            
            # Browser fingerprint headers
            'User-Agent': browser_config['user_agent'],
            'Sec-Ch-Ua': browser_config['sec_ch_ua'],
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': browser_config['platform'],
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            
            # SheerID client headers (from military module)
            'clientversion': '2.157.0',
            'clientname': 'jslib',
            'Origin': 'https://services.sheerid.com',
            
            # NewRelic tracking headers (anti-bot bypass)
            'newrelic': nr_headers['newrelic'],
            'traceparent': nr_headers['traceparent'],
            'tracestate': nr_headers['tracestate'],
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
            
            # Clear existing cookies to force new session
            self.http_client.cookies.clear()
            
            # Use random browser config for realistic headers
            browser_config = self._get_random_browser_config()
            
            # Request landing page to get new ID with full headers
            response = self.http_client.get(
                f"{SHEERID_BASE_URL}/verify/{PROGRAM_ID}/",
                follow_redirects=True,
                headers={
                    'User-Agent': browser_config['user_agent'],
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Pragma': 'no-cache',
                    'Cache-Control': 'no-cache',
                    'Sec-Ch-Ua': browser_config['sec_ch_ua'],
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': browser_config['platform'],
                }
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
            error_msg = data.get('errorMessage', 'Unknown')
            error_code = data.get('errorCode', 'N/A')
            segment = data.get('segment', 'N/A')
            # Log full response for debugging
            logger.error(f"[DEBUG] SheerID Error Response: {data}")
            self._update_status("ERROR", f"❌ API Error: {error_msg} (code: {error_code})")
            self._update_status("DEBUG", f"Segment: {segment}, Full: {str(data)[:200]}")
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
                
                # REJECTED - Fail immediately (No Doc Retry)
                if current_step == 'rejected':
                    reasons = data.get('rejectionReasons', [])
                    reason_text = ', '.join(reasons) if reasons else 'Unknown'
                    self._update_status("REJECTED", f"Document rejected: {reason_text}", "rejected")
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
        
        # Connection Info
        flag = self._get_country_flag(self.ip_country)
        self._update_status("CONN", f"IP: {flag} {self.current_ip}")
        self._update_status("WARNING", f"⚠️ Đảm bảo browser dùng CÙNG IP: {self.current_ip}")
        
        MAX_ATTEMPTS = 1  # Single attempt, then rotate and stop for user action
        mode_text = "⚡ FAST MODE" if fast_mode else "📄 NORMAL MODE"
        self._update_status("MODE", mode_text)
        
        # Track last error for final message
        last_error = "Unknown"
        last_step = "Unknown"
        
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._update_status("ATTEMPT", f"\n🎯 ━━━━━━━━ THỬ LẦN {attempt}/{MAX_ATTEMPTS} ━━━━━━━━")
            
            # 1. Select random district template and get matching teacher
            district_template = random.choice(DISTRICT_TEMPLATES)
            teacher = generate_teacher_info(district=district_template)
            
            email = self.custom_email if self.custom_email else teacher['email']
            school_id = teacher.get('school_id', DEFAULT_SCHOOL_ID) or DEFAULT_SCHOOL_ID
            school = SCHOOLS.get(str(school_id), SCHOOLS[DEFAULT_SCHOOL_ID])
            
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
                    # Fall through to rotation logic below
                
                elif result.get('success'):
                    self._update_status("SUCCESS", f"✅ VERIFY THÀNH CÔNG!")
                    return result
                
                elif result.get('rejected'):
                    reasons = result.get('rejection_reasons', [])
                    last_error = f"Rejected: {', '.join(reasons) if reasons else 'Unknown'}"
                    last_step = "Step 3: Poll Result"
                    self._update_status("FAIL", f"❌ Thất bại: {last_error}")
                
                elif result.get('error'):
                    last_error = result.get('message', 'API Error')
                    last_step = "API Call"
                    self._update_status("FAIL", f"❌ Lỗi API: {last_error}")
                
                else:
                    last_error = str(result)[:100]
                    last_step = "Unknown"
                    self._update_status("FAIL", f"❌ Result unknown: {last_error}")
                
            except Exception as e:
                last_error = str(e)
                last_step = "Exception"
                self._update_status("ERROR", f"❌ Lỗi: {e}")
        
        # === FAIL: Rotate session and STOP for user action ===
        self._update_status("FINAL", "━━━ KẾT QUẢ ━━━")
        self._update_status("FINAL", f"❌ Thất bại - {last_error}")
        
        # Rotate proxy session
        self._rotate_proxy_session()
        
        # Show clear instructions
        self._update_status("ACTION", "")
        self._update_status("ACTION", "📋 ĐÃ ĐỔI SESSION. HÃY LÀM THEO CÁC BƯỚC:")
        self._update_status("ACTION", "1️⃣ Mở SwitchyOmega → Đổi username (xem session mới ở trên)")
        self._update_status("ACTION", "2️⃣ Mở Incognito → Vào ChatGPT → SheerID")
        self._update_status("ACTION", "3️⃣ Export cookies MỚI")
        self._update_status("ACTION", "4️⃣ Paste cookies và Verify lại!")
        
        return {'success': False, 'needs_new_cookies': True, 'message': f'{last_step} - {last_error}'}

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
            error_data = status.get('data', {})
            error_msg = error_data.get('errorMessage', 'Unknown')
            error_code = error_data.get('errorCode', 'N/A')
            logger.error(f"[DEBUG] Verification Error State: {error_data}")
            self._update_status("DEBUG", f"Error state: {error_msg} (code: {error_code})")
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
