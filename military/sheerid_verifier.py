"""SheerID Military Verification"""
import re
import random
import logging
import time
import httpx
from typing import Dict, Optional, Tuple, List

from . import config
from .name_generator import generate_veteran_info, generate_email, mark_veteran_used
from .living_veteran_search import get_random_living_veteran

# Import proxy manager
try:
    from config.proxy_manager import get_proxy_url, get_ip_display
except ImportError:
    def get_proxy_url(): return None
    def get_ip_display(): return None

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SheerIDVerifier:
    """SheerID Military (Veteran) Verifier"""
    
    def __init__(self, verification_id: str, email: str = None, use_living_veteran: bool = False):
        self.verification_id = verification_id
        self.email = email  # User-provided email for email verification loop
        self.use_living_veteran = use_living_veteran  # Use living veteran data
        
        # Initialize httpx client with proxy support
        proxy_url = get_proxy_url()
        if proxy_url:
            self.http_client = httpx.Client(timeout=30.0, proxy=proxy_url)
            logger.info(f"Using proxy: {proxy_url[:40]}...")
        else:
            self.http_client = httpx.Client(timeout=30.0)
            logger.info("No proxy configured")
        
        self.debug_info = {}  # Store debug information
    
    def __del__(self):
        if hasattr(self, "http_client"):
            self.http_client.close()
    
    @staticmethod
    def _generate_device_fingerprint() -> str:
        chars = '0123456789abcdef'
        return ''.join(random.choice(chars) for _ in range(32))
    
    @staticmethod
    def parse_verification_id(url: str) -> Optional[str]:
        """Extract verification ID from URL"""
        match = re.search(r"verificationId=([a-f0-9]+)", url, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    # Error categories and recommended actions
    ERROR_ACTIONS = {
        "notApproved": {"action": "change_ip", "message": "Not approved - try different IP"},
        "limitExceeded": {"action": "change_profile", "message": "Profile overused - try different veteran"},
        "invalidPersonInfo": {"action": "change_profile", "message": "Invalid info - try different veteran"},
        "invalidBirthDate": {"action": "change_profile", "message": "Invalid birth date"},
        "verificationLimitExceeded": {"action": "wait", "message": "Rate limited - wait and retry"},
        "maxRetriesReached": {"action": "wait", "message": "Max retries - wait 24h"},
    }
    
    @classmethod
    def categorize_error(cls, error_ids: list) -> Dict:
        """Categorize error and suggest action."""
        for error_id in error_ids:
            if error_id in cls.ERROR_ACTIONS:
                return cls.ERROR_ACTIONS[error_id]
        return {"action": "unknown", "message": "Unknown error"}
    
    # Valid military organization IDs
    VALID_ORG_IDS = {4070, 4071, 4072, 4073, 4074, 4544268}
    
    def _validate_veteran_info(self, veteran_info: Dict, email: str) -> Tuple[bool, List[str]]:
        """Validate all fields before submission to avoid flag/reject."""
        errors = []
        
        # 1. First Name validation
        first = veteran_info.get("first_name", "")
        if not first:
            errors.append("First name is empty")
        elif first != first.strip():
            errors.append(f"First name has extra spaces: '{first}'")
        
        # 2. Last Name validation
        last = veteran_info.get("last_name", "")
        if not last:
            errors.append("Last name is empty")
        elif last != last.strip():
            errors.append(f"Last name has extra spaces: '{last}'")
        
        # 3. Birth date validation (must be YYYY-MM-DD)
        birth = veteran_info.get("birth_date", "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", birth):
            errors.append(f"Invalid birth date format: '{birth}' (expected YYYY-MM-DD)")
        
        # 4. Branch/Organization validation
        org = veteran_info.get("organization", {})
        org_id = org.get("id")
        org_name = org.get("name")
        if org_id not in self.VALID_ORG_IDS:
            errors.append(f"Invalid organization ID: {org_id}")
        if not org_name:
            errors.append("Organization name is empty")
        
        # 5. Discharge date validation (must be 2025)
        discharge = veteran_info.get("discharge_date", "")
        if not discharge.startswith("2025"):
            errors.append(f"Discharge date must be in 2025: '{discharge}'")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", discharge):
            errors.append(f"Invalid discharge date format: '{discharge}'")
        
        # 6. Email validation
        if not email or "@" not in email:
            errors.append(f"Invalid email: '{email}'")
        
        return len(errors) == 0, errors
    
    def _log_pre_submit(self, veteran_info: Dict, email: str):
        """Log all fields before submission for debugging."""
        logger.info("=" * 50)
        logger.info("PRE-SUBMIT VALIDATION")
        logger.info("=" * 50)
        
        first = veteran_info.get("first_name", "")
        last = veteran_info.get("last_name", "")
        birth = veteran_info.get("birth_date", "")
        org = veteran_info.get("organization", {})
        discharge = veteran_info.get("discharge_date", "")
        
        logger.info(f"  First Name: '{first}' (len={len(first)})")
        logger.info(f"  Last Name:  '{last}' (len={len(last)})")
        logger.info(f"  Full Name:  '{first} {last}'")
        logger.info(f"  Birth Date: '{birth}'")
        logger.info(f"  Branch:     '{org.get('name')}' (ID={org.get('id')})")
        logger.info(f"  Discharge:  '{discharge}'")
        logger.info(f"  Email:      '{email}'")
        logger.info("=" * 50)
    
    def _sheerid_request(
        self, method: str, url: str, body: Optional[Dict] = None
    ) -> Tuple[Dict, int]:
        """Send SheerID API request"""
        headers = {
            "Content-Type": "application/json",
        }
        
        try:
            response = self.http_client.request(
                method=method, url=url, json=body, headers=headers
            )
            try:
                data = response.json()
            except Exception:
                data = {"raw_response": response.text}
            return data, response.status_code
        except Exception as e:
            logger.error(f"SheerID request failed: {e}")
            raise
    
    def _collect_military_status(self) -> Tuple[Dict, int]:
        """Step 1: Collect Military Status"""
        url = f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/collectMilitaryStatus"
        
        body = {
            "status": config.MILITARY_STATUS  # "VETERAN"
        }
        
        logger.info(f"Step 1: Collecting military status (VETERAN)...")
        data, status_code = self._sheerid_request("POST", url, body)
        
        # Store debug info
        self.debug_info["step1_request"] = body
        self.debug_info["step1_response"] = data
        self.debug_info["step1_status"] = status_code
        
        return data, status_code
    
    def _collect_personal_info(self, veteran_info: Dict, submission_url: str = None) -> Tuple[Dict, int]:
        """Step 2: Collect Inactive Military Personal Info"""
        
        # Use provided submission URL or construct default
        if submission_url:
            url = submission_url
        else:
            url = f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/collectInactiveMilitaryPersonalInfo"
        
        # Use user-provided email or generate random one
        if self.email:
            email = self.email
            logger.info(f"  Using user-provided email: {email}")
        else:
            email = generate_email(veteran_info["first_name"], veteran_info["last_name"])
            logger.info(f"  Using generated email: {email}")
        
        body = {
            "firstName": veteran_info["first_name"],
            "lastName": veteran_info["last_name"],
            "birthDate": veteran_info["birth_date"],
            "email": email,
            "phoneNumber": "",
            "organization": {
                "id": veteran_info["organization"]["id"],
                "name": veteran_info["organization"]["name"]
            },
            "dischargeDate": veteran_info["discharge_date"],
            "locale": "en-US",
            "country": "US",
            "metadata": {
                "marketConsentValue": False,
                "refererUrl": "",
                "verificationId": self.verification_id,
                "flags": '{"doc-upload-considerations":"default","doc-upload-may24":"default","doc-upload-redesign-use-legacy-message-keys":false,"docUpload-assertion-checklist":"default","include-cvec-field-france-student":"not-labeled-optional","org-search-overlay":"default","org-selected-display":"default"}',
                "submissionOptIn": "By submitting the personal information above, I acknowledge that my personal information is being collected under the privacy policy of the business from which I am seeking a discount, and I understand that my personal information will be shared with SheerID as a processor/third-party service provider in order for SheerID to confirm my eligibility for a special offer."
            }
        }
        
        logger.info(f"Step 2: Submitting personal info...")
        logger.info(f"  Name: {veteran_info['first_name']} {veteran_info['last_name']}")
        logger.info(f"  Birth: {veteran_info['birth_date']}")
        logger.info(f"  Branch: {veteran_info['organization']['name']}")
        logger.info(f"  Discharge: {veteran_info['discharge_date']}")
        
        data, status_code = self._sheerid_request("POST", url, body)
        
        # Store debug info
        self.debug_info["step2_request"] = {
            "firstName": veteran_info["first_name"],
            "lastName": veteran_info["last_name"],
            "birthDate": veteran_info["birth_date"],
            "email": email,
            "organization": veteran_info["organization"],
            "dischargeDate": veteran_info["discharge_date"]
        }
        self.debug_info["step2_response"] = data
        self.debug_info["step2_status"] = status_code
        
        return data, status_code
    
    def confirm_email(self, email_token: str) -> Tuple[Dict, int]:
        """Step 3: Confirm email verification with token"""
        url = f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/emailLoop"
        
        body = {
            "emailToken": email_token
        }
        
        logger.info(f"Step 3: Confirming email with token {email_token}...")
        data, status_code = self._sheerid_request("POST", url, body)
        
        self.debug_info["step3_request"] = body
        self.debug_info["step3_response"] = data
        self.debug_info["step3_status"] = status_code
        
        return data, status_code
    
    def verify(self) -> Dict:
        """Execute military verification flow"""
        try:
            # Generate veteran info - use living veteran if flag is set
            if self.use_living_veteran:
                veteran_info = get_random_living_veteran()
                logger.info("Using LIVING veteran data")
            else:
                veteran_info = generate_veteran_info()
            
            if not veteran_info:
                return {
                    "success": False,
                    "message": "Failed to generate veteran info - no profiles available",
                    "verification_id": self.verification_id,
                    "debug_info": self.debug_info
                }
            
            # Store veteran info for debugging
            self.debug_info["veteran_info"] = {
                "name": f"{veteran_info['first_name']} {veteran_info['last_name']}",
                "birth_date": veteran_info["birth_date"],
                "discharge_date": veteran_info["discharge_date"],
                "branch": veteran_info["branch"],
                "organization": veteran_info["organization"]
            }
            
            # Get email to use
            email = self.email or generate_email(veteran_info)
            
            # === PRE-SUBMIT VALIDATION ===
            self._log_pre_submit(veteran_info, email)
            
            is_valid, errors = self._validate_veteran_info(veteran_info, email)
            if not is_valid:
                logger.error("VALIDATION FAILED!")
                for err in errors:
                    logger.error(f"  - {err}")
                return {
                    "success": False,
                    "message": f"Validation failed: {'; '.join(errors)}",
                    "verification_id": self.verification_id,
                    "debug_info": self.debug_info
                }
            
            logger.info("[OK] All fields validated successfully")
            logger.info(f"Verification ID: {self.verification_id}")
            logger.info(f"Using veteran: {veteran_info['first_name']} {veteran_info['last_name']}")
            
            # Add human-like delay before starting (simulating page load and reading)
            initial_delay = random.uniform(2.0, 4.0)
            logger.info(f"Waiting {initial_delay:.1f}s before starting (simulating page load)...")
            time.sleep(initial_delay)
            
            # Step 1: Collect Military Status
            step1_data, step1_status = self._collect_military_status()
            
            if step1_status != 200:
                error_ids = step1_data.get("errorIds", [])
                error_info = self.categorize_error(error_ids)
                return {
                    "success": False,
                    "message": f"Step 1 failed (HTTP {step1_status}): {', '.join(error_ids) if error_ids else 'Unknown error'}",
                    "verification_id": self.verification_id,
                    "step": "collectMilitaryStatus",
                    "error_ids": error_ids,
                    "suggested_action": error_info["action"],
                    "action_message": error_info["message"],
                    "debug_info": self.debug_info
                }
            
            if step1_data.get("currentStep") == "error":
                error_ids = step1_data.get("errorIds", [])
                error_info = self.categorize_error(error_ids)
                return {
                    "success": False,
                    "message": f"Step 1 error: {', '.join(error_ids)}",
                    "verification_id": self.verification_id,
                    "step": "collectMilitaryStatus",
                    "error_ids": error_ids,
                    "suggested_action": error_info["action"],
                    "action_message": error_info["message"],
                    "debug_info": self.debug_info
                }
            
            logger.info(f"✅ Step 1 complete: {step1_data.get('currentStep')}")
            
            # Get submission URL from step 1 response
            submission_url = step1_data.get("submissionUrl")
            
            # Add human-like delay between steps (simulating form filling)
            # This is important to avoid bot detection
            form_delay = random.uniform(5.0, 10.0)
            logger.info(f"⏳ Waiting {form_delay:.1f}s before submitting personal info (simulating form filling)...")
            time.sleep(form_delay)
            
            # Step 2: Collect Personal Info
            step2_data, step2_status = self._collect_personal_info(veteran_info, submission_url)
            
            if step2_status != 200:
                error_ids = step2_data.get("errorIds", [])
                return {
                    "success": False,
                    "message": f"Step 2 failed (HTTP {step2_status}): {', '.join(error_ids) if error_ids else 'Unknown error'}",
                    "verification_id": self.verification_id,
                    "step": "collectInactiveMilitaryPersonalInfo",
                    "error_ids": error_ids,
                    "debug_info": self.debug_info
                }
            
            if step2_data.get("currentStep") == "error":
                error_ids = step2_data.get("errorIds", [])
                return {
                    "success": False,
                    "message": f"Step 2 error: {', '.join(error_ids)}",
                    "verification_id": self.verification_id,
                    "step": "collectInactiveMilitaryPersonalInfo",
                    "error_ids": error_ids,
                    "debug_info": self.debug_info
                }
            
            logger.info(f"✅ Step 2 complete: {step2_data.get('currentStep')}")
            
            # Check final status
            current_step = step2_data.get("currentStep", "")
            redirect_url = step2_data.get("redirectUrl")
            reward_code = step2_data.get("rewardCode") or step2_data.get("rewardData", {}).get("rewardCode")
            
            if current_step == "success":
                # Mark veteran as used to avoid repeat
                mark_veteran_used(
                    f"{veteran_info['first_name']} {veteran_info['last_name']}",
                    veteran_info['birth_date']
                )
                return {
                    "success": True,
                    "pending": False,
                    "message": "Military verification successful!",
                    "verification_id": self.verification_id,
                    "redirect_url": redirect_url,
                    "reward_code": reward_code,
                    "current_step": current_step,
                    "debug_info": self.debug_info
                }
            elif current_step == "docUpload":
                # Needs document upload (shouldn't happen for military but handle it)
                return {
                    "success": True,
                    "pending": True,
                    "message": "Verification submitted, document upload may be required",
                    "verification_id": self.verification_id,
                    "redirect_url": redirect_url,
                    "current_step": current_step,
                    "debug_info": self.debug_info
                }
            else:
                # Pending or other status
                return {
                    "success": True,
                    "pending": True,
                    "message": f"Verification submitted, current status: {current_step}",
                    "verification_id": self.verification_id,
                    "redirect_url": redirect_url,
                    "current_step": current_step,
                    "debug_info": self.debug_info
                }
        
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return {
                "success": False,
                "message": str(e),
                "verification_id": self.verification_id,
                "debug_info": self.debug_info
            }


def main():
    """Command line interface for testing"""
    import sys
    
    print("=" * 60)
    print("SheerID Military (Veteran) Verification Tool")
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter SheerID verification URL: ").strip()
    
    if not url:
        print("❌ Error: No URL provided")
        sys.exit(1)
    
    verification_id = SheerIDVerifier.parse_verification_id(url)
    if not verification_id:
        print("❌ Error: Invalid verification ID format")
        sys.exit(1)
    
    print(f"✅ Parsed verification ID: {verification_id}")
    print()
    
    verifier = SheerIDVerifier(verification_id)
    result = verifier.verify()
    
    print()
    print("=" * 60)
    print("Result:")
    print("=" * 60)
    print(f"Status: {'✅ Success' if result['success'] else '❌ Failed'}")
    print(f"Message: {result['message']}")
    
    if result.get("redirect_url"):
        print(f"Redirect URL: {result['redirect_url']}")
    if result.get("reward_code"):
        print(f"Reward Code: {result['reward_code']}")
    
    # Print debug info
    if not result['success'] and result.get('debug_info'):
        print()
        print("Debug Info:")
        debug = result['debug_info']
        if debug.get('veteran_info'):
            vi = debug['veteran_info']
            print(f"  Veteran: {vi.get('name')}")
            print(f"  Birth: {vi.get('birth_date')}")
            print(f"  Branch: {vi.get('branch')}")
            print(f"  Discharge: {vi.get('discharge_date')}")
        if debug.get('step1_status'):
            print(f"  Step 1 Status: {debug['step1_status']}")
        if debug.get('step2_status'):
            print(f"  Step 2 Status: {debug['step2_status']}")
    
    print("=" * 60)
    
    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
