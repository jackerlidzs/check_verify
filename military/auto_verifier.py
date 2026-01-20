"""
Full Auto Military Verification
- Uses Playwright with proxy for browser automation
- Uses temp mail API for email verification
- Single IP throughout entire flow
"""
import re
import time
import random
import logging
import httpx
from typing import Dict, Optional, Tuple

from . import config
from .name_generator import generate_veteran_info, mark_veteran_used
from .sheerid_verifier import SheerIDVerifier
from .living_veteran_search import get_random_living_veteran

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import proxy manager
try:
    from config.proxy_manager import get_proxy_url
except ImportError:
    def get_proxy_url(): return None


class TempMailClient:
    """Temp mail client using mail.tm API"""
    
    BASE_URL = "https://api.mail.tm"
    
    def __init__(self, proxy_url: str = None):
        self.proxy_url = proxy_url
        self.http = httpx.Client(timeout=30.0, proxy=proxy_url)
        self.email = None
        self.password = None
        self.token = None
        self.account_id = None
    
    def create_account(self) -> str:
        """Create a temp email account and return the address."""
        # Get available domains
        domains_resp = self.http.get(f"{self.BASE_URL}/domains")
        if domains_resp.status_code != 200:
            raise Exception(f"Failed to get domains: {domains_resp.text}")
        
        domains = domains_resp.json().get("hydra:member", [])
        if not domains:
            raise Exception("No domains available")
        
        domain = domains[0]["domain"]
        
        # Generate random email
        username = f"vet{random.randint(10000, 99999)}"
        self.email = f"{username}@{domain}"
        self.password = f"Pass{random.randint(100000, 999999)}!"
        
        # Create account
        create_resp = self.http.post(
            f"{self.BASE_URL}/accounts",
            json={"address": self.email, "password": self.password}
        )
        
        if create_resp.status_code not in [200, 201]:
            raise Exception(f"Failed to create account: {create_resp.text}")
        
        self.account_id = create_resp.json().get("id")
        
        # Login to get token
        login_resp = self.http.post(
            f"{self.BASE_URL}/token",
            json={"address": self.email, "password": self.password}
        )
        
        if login_resp.status_code != 200:
            raise Exception(f"Failed to login: {login_resp.text}")
        
        self.token = login_resp.json().get("token")
        logger.info(f"Created temp email: {self.email}")
        
        return self.email
    
    def wait_for_email(self, timeout: int = 120, poll_interval: int = 5) -> Optional[Dict]:
        """Wait for SheerID verification email."""
        if not self.token:
            raise Exception("Not logged in")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        start_time = time.time()
        
        logger.info(f"Waiting for email (timeout: {timeout}s)...")
        
        while time.time() - start_time < timeout:
            messages_resp = self.http.get(
                f"{self.BASE_URL}/messages",
                headers=headers
            )
            
            if messages_resp.status_code == 200:
                messages = messages_resp.json().get("hydra:member", [])
                for msg in messages:
                    # Check if it's from SheerID
                    if "sheerid" in msg.get("from", {}).get("address", "").lower():
                        # Get full message
                        msg_id = msg.get("id")
                        full_msg = self.http.get(
                            f"{self.BASE_URL}/messages/{msg_id}",
                            headers=headers
                        )
                        if full_msg.status_code == 200:
                            return full_msg.json()
            
            time.sleep(poll_interval)
            logger.info(f"  Checking email... ({int(time.time() - start_time)}s)")
        
        logger.warning("Email timeout - no SheerID email received")
        return None
    
    def extract_token_from_email(self, email_data: Dict) -> Optional[str]:
        """Extract verification token from email content."""
        # Get HTML and text content - handle both string and list types
        html = email_data.get("html", "") or ""
        text = email_data.get("text", "") or ""
        
        # Handle list type (mail.tm sometimes returns list of content parts)
        if isinstance(html, list):
            html = " ".join(str(h) for h in html)
        if isinstance(text, list):
            text = " ".join(str(t) for t in text)
        
        # Convert to string if needed
        html = str(html)
        text = str(text)
        
        logger.info(f"  Parsing email content (html: {len(html)} chars, text: {len(text)} chars)")
        
        # Look for emailToken in links
        patterns = [
            r"emailToken[=%3D](\d+)",
            r"emailToken[=:](\d+)",
            r"token[=:](\d+)",
            r"code[=:](\d+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html) or re.search(pattern, text)
            if match:
                logger.info(f"  Found token via pattern: {pattern}")
                return match.group(1)
        
        # Look for 6-digit code in text
        code_match = re.search(r"\b(\d{6})\b", text) or re.search(r"\b(\d{6})\b", html)
        if code_match:
            logger.info("  Found 6-digit code")
            return code_match.group(1)
        
        logger.warning("  Could not extract token from email")
        return None
    
    def close(self):
        self.http.close()


class AutoMilitaryVerifier:
    """Full auto military verification with single IP."""
    
    def __init__(self, verification_url: str = None):
        self.proxy_url = get_proxy_url()
        self.temp_mail = None
        self.verifier = None
        self.verification_url = verification_url
    
    def run_with_url(self, verification_url: str) -> Dict:
        """Run verification with user-provided URL."""
        self.verification_url = verification_url
        return self.run()
    
    def run(self) -> Dict:
        """Run full auto verification flow."""
        try:
            logger.info("=" * 60)
            logger.info("FULL AUTO MILITARY VERIFICATION")
            logger.info("=" * 60)
            
            # Step 0: Create temp email
            self.temp_mail = TempMailClient(self.proxy_url)
            email = self.temp_mail.create_account()
            
            # Step 1: Get verification ID
            if self.verification_url:
                verification_id = SheerIDVerifier.parse_verification_id(self.verification_url)
                if not verification_id:
                    return {"success": False, "message": "Invalid verification URL"}
            else:
                return {"success": False, "message": "Verification URL required"}
            
            logger.info(f"Verification ID: {verification_id}")
            logger.info(f"Email: {email}")
            
            # Step 2: Run SheerID verification with LIVING veteran data
            self.verifier = SheerIDVerifier(verification_id, email=email, use_living_veteran=True)
            result = self.verifier.verify()
            
            if not result.get("success"):
                return result
            
            current_step = result.get("current_step", "")
            
            # Step 3: If emailLoop, wait for and confirm email
            if current_step == "emailLoop":
                logger.info("Waiting for verification email...")
                
                email_data = self.temp_mail.wait_for_email(timeout=120)
                
                if not email_data:
                    return {
                        "success": True,
                        "pending": True,
                        "message": "Email verification pending - no email received",
                        "verification_id": verification_id,
                        "email": email
                    }
                
                # Extract token
                token = self.temp_mail.extract_token_from_email(email_data)
                
                if not token:
                    return {
                        "success": True,
                        "pending": True,
                        "message": "Could not extract token from email",
                        "verification_id": verification_id,
                        "email": email
                    }
                
                logger.info(f"Got email token: {token}")
                
                # Confirm email
                confirm_data, confirm_status = self.verifier.confirm_email(token)
                
                if confirm_status != 200:
                    return {
                        "success": False,
                        "message": f"Email confirmation failed: {confirm_data}",
                        "verification_id": verification_id
                    }
                
                final_step = confirm_data.get("currentStep", "")
                
                if final_step == "success":
                    redirect_url = confirm_data.get("redirectUrl")
                    return {
                        "success": True,
                        "pending": False,
                        "message": "Military verification successful!",
                        "verification_id": verification_id,
                        "redirect_url": redirect_url
                    }
                elif final_step == "error":
                    error_ids = confirm_data.get("errorIds", [])
                    return {
                        "success": False,
                        "message": f"Error: {', '.join(error_ids)}",
                        "verification_id": verification_id,
                        "data": confirm_data
                    }
                else:
                    return {
                        "success": True,
                        "pending": True,
                        "message": f"Final step: {final_step}",
                        "verification_id": verification_id,
                        "data": confirm_data
                    }
            
            # Already success without emailLoop
            return result
            
        except Exception as e:
            logger.error(f"Auto verification failed: {e}")
            return {"success": False, "message": str(e)}
        
        finally:
            if self.temp_mail:
                self.temp_mail.close()


def main():
    """CLI for auto military verification."""
    import sys
    
    print("=" * 60)
    print("FULL AUTO MILITARY VERIFICATION")
    print("=" * 60)
    print()
    
    # Get URL from command line or user input
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter SheerID verification URL: ").strip()
    
    if not url:
        print("[ERROR] No URL provided")
        return 1
    
    auto = AutoMilitaryVerifier(verification_url=url)
    result = auto.run()
    
    print()
    print("=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(f"Status: {'SUCCESS' if result.get('success') else 'FAILED'}")
    print(f"Message: {result.get('message')}")
    
    if result.get("redirect_url"):
        print(f"Redirect: {result['redirect_url']}")
    if result.get("email"):
        print(f"Temp Email: {result['email']}")
    
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    exit(main())

