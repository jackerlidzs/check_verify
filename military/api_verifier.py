"""
SheerID API-based Military Verification
Based on reference implementation - faster and more reliable than browser
"""
import json
import time
import re
import uuid
import random
import base64
import hashlib
import argparse
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False
    import requests

from .email_client import EmailClient, load_email_config
from .dedup_tracker import DeduplicationTracker


# ============================================================
# ERROR MESSAGES & SOLUTIONS
# ============================================================
ERROR_HELP = {
    "403 Forbidden": {
        "cause": "accessToken expired or invalid",
        "solution": "Get new token: Login chatgpt.com → DevTools(F12) → Console → Run:\n"
                   "   JSON.parse(document.getElementById('__NEXT_DATA__').textContent).props.pageProps.accessToken"
    },
    "401 Unauthorized": {
        "cause": "Invalid or malformed accessToken",
        "solution": "Check token format, must be a long JWT string. Get fresh token from chatgpt.com"
    },
    "Not approved": {
        "cause": "Veteran data not in DoD/DEERS database OR IP blocked",
        "solution": "1. Use proxy (add to config)\n   2. Try different veteran data\n   3. Data may be fake/ineligible"
    },
    "Document upload required": {
        "cause": "Auto-verification failed - data not found in DoD/DEERS",
        "solution": "This veteran's data doesn't match military records. Try different data."
    },
    "Email connection failed": {
        "cause": "IMAP settings incorrect or blocked",
        "solution": "1. Check imap_server (gmail: imap.gmail.com)\n   2. Use App Password (not regular password)\n   3. Enable IMAP in Gmail settings"
    },
    "Data already verified": {
        "cause": "This veteran identity was already used for verification",
        "solution": "Try different veteran data. Each identity can only verify once."
    },
    "Already used, skipping": {
        "cause": "Data exists in used.txt (dedup tracking)",
        "solution": "Use --no-dedup flag to skip dedup check, or delete used.txt"
    },
    "verificationLimitExceeded": {
        "cause": "Too many verification attempts from this IP/email",
        "solution": "1. Use proxy\n   2. Wait 24 hours\n   3. Use different email"
    },
    "Email not received": {
        "cause": "Verification email not found in inbox",
        "solution": "1. Check spam folder\n   2. Verify IMAP settings\n   3. Wait longer (increase timeout)"
    },
}


# API Endpoints
SHEERID_API = "https://services.sheerid.com/rest/v2"
CHATGPT_API = "https://chatgpt.com/backend-api"
DEFAULT_PROGRAM_ID = "690415d58971e73ca187d8c9"

# Branch Organization IDs
BRANCH_ORG_MAP = {
    "Army": {"id": 4070, "name": "Army"},
    "Air Force": {"id": 4073, "name": "Air Force"},
    "Navy": {"id": 4072, "name": "Navy"},
    "Marine Corps": {"id": 4071, "name": "Marine Corps"},
    "Coast Guard": {"id": 4074, "name": "Coast Guard"},
    "Space Force": {"id": 4544268, "name": "Space Force"},
    "Army National Guard": {"id": 4075, "name": "Army National Guard"},
    "Army Reserve": {"id": 4076, "name": "Army Reserve"},
    "Air National Guard": {"id": 4079, "name": "Air National Guard"},
    "Air Force Reserve": {"id": 4080, "name": "Air Force Reserve"},
    "Navy Reserve": {"id": 4078, "name": "Navy Reserve"},
    "Marine Corps Reserve": {"id": 4077, "name": "Marine Corps Forces Reserve"},
    "Coast Guard Reserve": {"id": 4081, "name": "Coast Guard Reserve"},
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"


def log_error(error_key: str, extra: str = ""):
    """Print detailed error with cause and solution."""
    print()
    print("=" * 60)
    print(f"   ❌ ERROR: {error_key}")
    print("=" * 60)
    
    if error_key in ERROR_HELP:
        info = ERROR_HELP[error_key]
        print(f"   CAUSE: {info['cause']}")
        print()
        print(f"   SOLUTION:")
        for line in info['solution'].split('\n'):
            print(f"      {line}")
    
    if extra:
        print()
        print(f"   DETAILS: {extra}")
    
    print("=" * 60)
    print()


def log_success(message: str):
    """Print success message."""
    print()
    print("=" * 60)
    print(f"   ✅ SUCCESS: {message}")
    print("=" * 60)
    print()


def log_step(step_num: int, total: int, description: str):
    """Print step progress."""
    print(f"   [{step_num}/{total}] {description}")


def log_info(message: str):
    """Print info message."""
    print(f"   ℹ️  {message}")


def log_warn(message: str):
    """Print warning message."""
    print(f"   ⚠️  {message}")


def generate_fingerprint() -> str:
    """Generate device fingerprint hash."""
    data = f"{uuid.uuid4()}{time.time()}{random.random()}"
    return hashlib.sha256(data.encode()).hexdigest()


def generate_newrelic_headers() -> Dict[str, str]:
    """Generate NewRelic tracking headers."""
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


class APIVerifier:
    """SheerID API-based military verification."""
    
    def __init__(self, config: Dict, skip_dedup: bool = False):
        """Initialize verifier with config."""
        self.access_token = config.get('accessToken', '')
        self.program_id = config.get('programId', DEFAULT_PROGRAM_ID)
        self.email_config = config.get('email', {})
        self.email_address = self.email_config.get('email_address', '')
        self.skip_dedup = skip_dedup
        
        # Setup proxy
        proxy = config.get('proxy')
        self.proxies = None
        if proxy:
            self.proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            log_info(f"Using proxy: {proxy}")
        
        # Setup session
        if HAS_CLOUDSCRAPER:
            self.session = cloudscraper.create_scraper()
            log_info("Using cloudscraper for Cloudflare bypass")
        else:
            self.session = requests.Session()
            log_warn("cloudscraper not installed, may fail on Cloudflare")
        
        # Email client
        self.email_client = None
        if self.email_config:
            self.email_client = EmailClient(self.email_config)
            log_info(f"Email client configured: {self.email_address}")
        
        # Dedup tracker
        self.dedup = DeduplicationTracker()
    
    def _get_headers(self, sheerid: bool = False) -> Dict[str, str]:
        """Get request headers."""
        base = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        
        if sheerid:
            nr = generate_newrelic_headers()
            return {
                **base,
                "clientversion": "2.157.0",
                "clientname": "jslib",
                "newrelic": nr["newrelic"],
                "traceparent": nr["traceparent"],
                "tracestate": nr["tracestate"],
                "origin": "https://services.sheerid.com"
            }
        
        # ChatGPT API headers
        return {
            **base,
            "authorization": f"Bearer {self.access_token}",
            "origin": "https://chatgpt.com",
            "referer": "https://chatgpt.com/veterans-claim",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "oai-device-id": str(uuid.uuid4()),
            "oai-language": "en-US",
        }
    
    def create_verification(self) -> Optional[str]:
        """Step 1: Create verification ID from ChatGPT."""
        log_step(1, 5, "Creating verification request...")
        
        try:
            resp = self.session.post(
                f"{CHATGPT_API}/veterans/create_verification",
                headers=self._get_headers(),
                json={"program_id": self.program_id},
                timeout=30,
                proxies=self.proxies
            )
            
            if resp.status_code == 403:
                log_error("403 Forbidden")
                return None
            
            if resp.status_code == 401:
                log_error("401 Unauthorized")
                return None
            
            resp.raise_for_status()
            verification_id = resp.json().get("verification_id")
            print(f"       ✓ Verification ID: {verification_id[:20]}...")
            return verification_id
            
        except Exception as e:
            log_error("Create verification failed", str(e))
            return None
    
    def submit_military_status(self, verification_id: str) -> bool:
        """Step 2: Submit status as VETERAN."""
        log_step(2, 5, "Submitting military status (VETERAN)...")
        
        try:
            resp = self.session.post(
                f"{SHEERID_API}/verification/{verification_id}/step/collectMilitaryStatus",
                headers=self._get_headers(sheerid=True),
                json={"status": "VETERAN"},
                timeout=30,
                proxies=self.proxies
            )
            resp.raise_for_status()
            print("       ✓ Status: VETERAN submitted")
            return True
        except Exception as e:
            log_error("Submit status failed", str(e))
            return False
    
    def submit_personal_info(self, verification_id: str, veteran: Dict) -> Dict:
        """Step 3: Submit personal information."""
        log_step(3, 5, "Submitting personal info...")
        
        fingerprint = generate_fingerprint()
        referer = f"https://services.sheerid.com/verify/{self.program_id}/?verificationId={verification_id}"
        
        # Get branch info
        branch_name = veteran.get('branch_name', 'Army')
        branch_id = veteran.get('branch_id', 4070)
        
        # Format birth date (YYYY/MM/DD -> YYYY-MM-DD)
        birth = veteran.get('birth', '').replace('/', '-')
        
        # Get discharge date
        discharge = veteran.get('discharge', '')
        
        print(f"       → Name: {veteran.get('firstname', '')} {veteran.get('lastname', '')}")
        print(f"       → Birth: {birth}")
        print(f"       → Branch: {branch_name} (ID: {branch_id})")
        print(f"       → Discharge: {discharge}")
        print(f"       → Email: {self.email_address}")
        
        payload = {
            "firstName": veteran.get('firstname', ''),
            "lastName": veteran.get('lastname', ''),
            "birthDate": birth,
            "email": self.email_address,
            "phoneNumber": "",
            "organization": {
                "id": branch_id,
                "name": branch_name
            },
            "dischargeDate": discharge,
            "deviceFingerprintHash": fingerprint,
            "locale": "en-US",
            "country": "US",
            "metadata": {
                "marketConsentValue": False,
                "refererUrl": referer,
                "verificationId": verification_id,
            }
        }
        
        headers = self._get_headers(sheerid=True)
        headers["referer"] = referer
        
        try:
            resp = self.session.post(
                f"{SHEERID_API}/verification/{verification_id}/step/collectInactiveMilitaryPersonalInfo",
                headers=headers,
                json=payload,
                timeout=30,
                proxies=self.proxies
            )
            
            data = resp.json()
            
            # Check for rate limit
            if resp.status_code == 429:
                log_error("verificationLimitExceeded")
                data["_already_verified"] = True
                return data
            
            error_ids = data.get("errorIds", [])
            if "verificationLimitExceeded" in error_ids:
                log_error("verificationLimitExceeded", str(error_ids))
                data["_already_verified"] = True
            
            current_step = data.get("currentStep", "unknown")
            print(f"       ✓ Response step: {current_step}")
            
            return data
            
        except Exception as e:
            log_error("Submit personal info failed", str(e))
            return {"error": str(e)}
    
    def wait_for_email(self, verification_id: str, max_wait: int = 60) -> Optional[str]:
        """Step 4: Wait for verification email and extract token."""
        log_step(4, 5, f"Waiting for verification email (max {max_wait}s)...")
        
        if not self.email_client:
            log_error("Email connection failed", "No email client configured")
            return None
        
        if not self.email_client.connect():
            log_error("Email connection failed", "Cannot connect to IMAP server")
            return None
        
        token = self.email_client.find_sheerid_token(verification_id, max_wait)
        self.email_client.disconnect()
        
        if token:
            print(f"       ✓ Token found: {token}")
        else:
            log_error("Email not received")
        
        return token
    
    def submit_email_token(self, verification_id: str, token: str) -> Dict:
        """Step 5: Submit email token."""
        log_step(5, 5, f"Submitting email token: {token}...")
        
        try:
            resp = self.session.post(
                f"{SHEERID_API}/verification/{verification_id}/step/emailLoop",
                headers=self._get_headers(sheerid=True),
                json={
                    "emailToken": token,
                    "deviceFingerprintHash": generate_fingerprint()
                },
                timeout=30,
                proxies=self.proxies
            )
            data = resp.json()
            print(f"       ✓ Email token submitted, step: {data.get('currentStep')}")
            return data
        except Exception as e:
            log_error("Submit email token failed", str(e))
            return {"error": str(e)}
    
    def verify(self, veteran: Dict) -> Dict:
        """Main verification flow."""
        firstname = veteran.get('firstname', '')
        lastname = veteran.get('lastname', '')
        birth = veteran.get('birth', '')
        
        # Check dedup
        if not self.skip_dedup and self.dedup.is_used(firstname, lastname, birth):
            log_error("Already used, skipping", f"{firstname} {lastname} ({birth})")
            return {"success": False, "message": "Already used, skipping", "skip": True}
        
        print()
        print("-" * 60)
        print(f"   VERIFYING: {firstname} {lastname}")
        print(f"   Branch: {veteran.get('branch_name', 'N/A')} | Birth: {birth}")
        print(f"   Discharge: {veteran.get('discharge', 'N/A')}")
        print("-" * 60)
        print()
        
        try:
            # Step 1
            verification_id = self.create_verification()
            if not verification_id:
                return {"success": False, "message": "Failed to create verification"}
            
            # Step 2
            if not self.submit_military_status(verification_id):
                return {"success": False, "message": "Failed to submit status"}
            
            # Step 3
            result = self.submit_personal_info(verification_id, veteran)
            step = result.get("currentStep")
            
            if result.get("_already_verified"):
                self.dedup.mark_used(firstname, lastname, birth)
                log_error("Data already verified")
                return {"success": False, "message": "Data already verified", "skip": True}
            
            if step == "success":
                self.dedup.mark_used(firstname, lastname, birth)
                log_success("Veteran verified! ChatGPT Plus activated!")
                return {"success": True, "message": "Verification successful!"}
            
            if step == "docUpload":
                log_error("Document upload required")
                return {"success": False, "message": "Document upload required"}
            
            if step == "error":
                error_ids = result.get('errorIds', [])
                error_key = error_ids[0] if error_ids else "Unknown error"
                log_error(error_key, str(error_ids))
                return {"success": False, "message": f"Error: {error_ids}"}
            
            # Step 4: Email loop
            if step == "emailLoop":
                token = self.wait_for_email(verification_id)
                if not token:
                    return {"success": False, "message": "Email not received"}
                
                # Step 5
                email_result = self.submit_email_token(verification_id, token)
                if email_result.get("currentStep") == "success":
                    self.dedup.mark_used(firstname, lastname, birth)
                    log_success("Email verified! ChatGPT Plus activated!")
                    return {"success": True, "message": "Verification successful!"}
                
                error_ids = email_result.get('errorIds', [])
                log_error("Email verify failed", str(error_ids))
                return {"success": False, "message": f"Email verify failed: {error_ids}"}
            
            log_error("Unknown step", step)
            return {"success": False, "message": f"Unknown step: {step}"}
            
        except Exception as e:
            log_error("Verification failed", str(e))
            return {"success": False, "error": str(e)}


def load_config() -> Dict:
    """Load config from file."""
    config_paths = [
        Path('config/military.json'),
        Path('military/config.json'),
        Path('config.json'),
    ]
    
    for path in config_paths:
        if path.exists():
            with open(path, 'r') as f:
                return json.load(f)
    
    return {}


def load_veterans(source: str = "all") -> List[Dict]:
    """Load veteran data from sources."""
    veterans = []
    
    source_files = {
        "all": [
            Path('military/data/real_veterans.json'),
            Path('military/data/ngl_veterans.json'),
            Path('military/data/anc_veterans.json'),
            Path('military/data/veterans_usa.json'),
            Path('military/data/all_under70_veterans.json'),
        ],
        "real": [Path('military/data/real_veterans.json')],
        "ngl": [Path('military/data/ngl_veterans.json')],
        "anc": [Path('military/data/anc_veterans.json')],
        "under70": [Path('military/data/all_under70_veterans.json')],
    }
    
    files = source_files.get(source, source_files["all"])
    
    for f in files:
        if f.exists():
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                veterans.extend(data)
                log_info(f"Loaded {len(data)} from {f.name}")
    
    return veterans


def load_veterans_from_file(file_path: str) -> List[Dict]:
    """Load veteran data from a custom file path."""
    veterans = []
    
    # Check if it's just a filename or full path
    path = Path(file_path)
    
    # Try multiple locations
    search_paths = [
        path,  # As-is
        Path('military/data') / path.name,  # In data folder
        Path('military/data') / file_path,  # In data folder (full input)
        Path(file_path),  # Absolute or relative path
    ]
    
    for p in search_paths:
        if p.exists():
            try:
                with open(p, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                    log_info(f"Loaded {len(data)} veterans from {p}")
                    return data
            except Exception as e:
                log_warn(f"Failed to load {p}: {e}")
    
    # Not found
    log_error("File not found", f"Could not find: {file_path}")
    log_info("Searched in:")
    for p in search_paths:
        print(f"      - {p}")
    
    return veterans


def select_veteran_file_interactive() -> List[Dict]:
    """Show interactive menu to select veteran data file."""
    data_dir = Path('military/data')
    
    # Find all JSON files in data folder
    json_files = []
    if data_dir.exists():
        json_files = sorted(data_dir.glob('*.json'))
    
    if not json_files:
        log_error("No data files found", f"No JSON files in {data_dir}")
        return []
    
    print()
    print("=" * 60)
    print("   📁 SELECT VETERAN DATA FILE")
    print("=" * 60)
    print()
    
    # List files with details
    file_info = []
    for i, f in enumerate(json_files, 1):
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                count = len(data)
        except:
            count = 0
        
        file_info.append((f, count))
        print(f"   [{i}] {f.name}")
        print(f"       └─ {count} veterans")
    
    print()
    print(f"   [0] Load ALL files")
    print()
    print("-" * 60)
    
    # Get user choice
    while True:
        try:
            choice = input("   Enter choice (0-{}): ".format(len(json_files))).strip()
            
            if not choice:
                choice = "0"  # Default to all
            
            choice_num = int(choice)
            
            if choice_num == 0:
                # Load all files
                print()
                log_info("Loading ALL data files...")
                veterans = []
                for f, count in file_info:
                    if count > 0:
                        with open(f, 'r', encoding='utf-8') as fp:
                            data = json.load(fp)
                            veterans.extend(data)
                            print(f"       ✓ {f.name}: {len(data)} loaded")
                return veterans
            
            elif 1 <= choice_num <= len(json_files):
                # Load selected file
                selected_file = json_files[choice_num - 1]
                print()
                log_info(f"Loading: {selected_file.name}")
                with open(selected_file, 'r', encoding='utf-8') as fp:
                    return json.load(fp)
            else:
                print("   ⚠️  Invalid choice, try again")
                
        except ValueError:
            print("   ⚠️  Please enter a number")
        except KeyboardInterrupt:
            print("\n   Cancelled")
            return []
        except Exception as e:
            log_error("Failed to load file", str(e))
            return []


def main():
    """Run verification."""
    parser = argparse.ArgumentParser(description="SheerID Military Verifier")
    parser.add_argument("--no-dedup", action="store_true", help="Skip deduplication check")
    parser.add_argument("-v", "--veteran-file", type=str, default=None,
                        help="Custom veteran JSON file path (e.g., -v anc_veterans.json)")
    parser.add_argument("--source", default="all", choices=["all", "real", "ngl", "anc", "under70"],
                        help="Data source to use (ignored if -v is provided)")
    parser.add_argument("--count", type=int, default=1, help="Number of verifications to attempt")
    args = parser.parse_args()
    
    print()
    print("=" * 60)
    print("   🎖️  SheerID API-based Military Verifier")
    print("=" * 60)
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.veteran_file:
        print(f"   Data File: {args.veteran_file}")
    else:
        print(f"   Source: {args.source}")
    print(f"   Count: {args.count}")
    print(f"   Skip Dedup: {args.no_dedup}")
    print("=" * 60)
    print()
    
    # Load config
    config = load_config()
    if not config.get('accessToken'):
        log_error("No accessToken in config", 
                  "Create config/military.json with accessToken field")
        print("\nExample config:")
        print(json.dumps({
            "accessToken": "YOUR_CHATGPT_ACCESS_TOKEN",
            "programId": "690415d58971e73ca187d8c9",
            "email": {
                "imap_server": "imap.gmail.com",
                "imap_port": 993,
                "email_address": "your@email.com",
                "email_password": "your_app_password",
                "use_ssl": True
            }
        }, indent=2))
        return
    
    # Load veterans
    if args.veteran_file:
        # Custom file path from command line
        veterans = load_veterans_from_file(args.veteran_file)
    else:
        # Show interactive menu to select file
        veterans = select_veteran_file_interactive()
    
    log_info(f"Total veterans loaded: {len(veterans)}")
    
    if not veterans:
        log_error("No veteran data found", 
                  "Add data to military/data/real_veterans.txt and run import_veterans.py")
        return
    
    # Init verifier
    verifier = APIVerifier(config, skip_dedup=args.no_dedup)
    
    # Run verifications
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    random.shuffle(veterans)
    
    for i, veteran in enumerate(veterans[:args.count], 1):
        print()
        print(f"{'=' * 60}")
        print(f"   ATTEMPT {i}/{args.count}")
        print(f"{'=' * 60}")
        
        result = verifier.verify(veteran)
        
        if result.get('success'):
            success_count += 1
        elif result.get('skip'):
            skip_count += 1
        else:
            fail_count += 1
        
        # Wait between attempts
        if i < args.count:
            wait = random.randint(3, 8)
            print(f"\n   ⏳ Waiting {wait}s before next attempt...")
            time.sleep(wait)
    
    # Summary
    print()
    print("=" * 60)
    print("   📊 SUMMARY")
    print("=" * 60)
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed:  {fail_count}")
    print(f"   ⏭️  Skipped: {skip_count}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
