"""
Mail.tm Email Client for SheerID Verification
Creates temporary emails and retrieves verification tokens automatically.

API Reference: https://docs.mail.tm/
- Free, no API key required
- Rate limit: 8 QPS per IP
"""
import httpx
import random
import string
import time
import re
import logging
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)


class MailTmClient:
    """
    Mail.tm API client for temporary email management.
    
    Flow:
    1. get_domains() - Get available domains
    2. create_account() - Create email account
    3. wait_for_sheerid_email() - Poll inbox for SheerID email
    4. extract_verification_token() - Parse verification token from email
    """
    
    BASE_URL = "https://api.mail.tm"
    
    def __init__(self, status_callback=None):
        """Initialize Mail.tm client.
        
        Args:
            status_callback: Optional callback(step, message) for status updates
        """
        self.status_callback = status_callback or (lambda s, m: None)
        self.http_client = httpx.Client(
            timeout=30.0,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        # Current session
        self.email_address = None
        self.password = None
        self.token = None
        self.account_id = None
    
    def _log(self, step: str, message: str):
        """Log status update."""
        logger.info(f"[{step}] {message}")
        self.status_callback(step, message)
    
    def get_domains(self) -> List[str]:
        """Get available email domains.
        
        Returns:
            List of available domain names
        """
        try:
            resp = self.http_client.get(f"{self.BASE_URL}/domains")
            
            if resp.status_code == 200:
                data = resp.json()
                # Handle paginated response
                if isinstance(data, dict) and 'hydra:member' in data:
                    domains = [d['domain'] for d in data['hydra:member'] if d.get('isActive')]
                else:
                    domains = [d['domain'] for d in data if d.get('isActive')]
                
                logger.info(f"Available domains: {domains}")
                return domains
            else:
                logger.error(f"Failed to get domains: {resp.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting domains: {e}")
            return []
    
    def _generate_random_username(self, length: int = 10) -> str:
        """Generate random username."""
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def _generate_password(self, length: int = 16) -> str:
        """Generate secure password."""
        chars = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(random.choice(chars) for _ in range(length))
    
    def create_account(self, custom_username: str = None) -> Tuple[str, str]:
        """Create new temporary email account.
        
        Args:
            custom_username: Optional custom username (random if not provided)
            
        Returns:
            Tuple of (email_address, password) or (None, None) on failure
        """
        # Get available domains
        domains = self.get_domains()
        if not domains:
            self._log("ERROR", "No domains available")
            return None, None
        
        domain = random.choice(domains)
        username = custom_username or self._generate_random_username()
        email_address = f"{username}@{domain}"
        password = self._generate_password()
        
        self._log("EMAIL", f"Creating: {email_address}")
        
        try:
            resp = self.http_client.post(
                f"{self.BASE_URL}/accounts",
                json={
                    "address": email_address,
                    "password": password
                }
            )
            
            if resp.status_code == 201:
                data = resp.json()
                self.email_address = email_address
                self.password = password
                self.account_id = data.get('id')
                
                # Login to get token
                self._login()
                
                self._log("EMAIL", f"Created: {email_address}")
                return email_address, password
            else:
                error = resp.text
                logger.error(f"Failed to create account: {resp.status_code} - {error}")
                
                # If username taken, retry with random
                if resp.status_code == 422:
                    self._log("RETRY", "Username taken, retrying...")
                    return self.create_account()
                
                return None, None
                
        except Exception as e:
            logger.error(f"Error creating account: {e}")
            return None, None
    
    def _login(self) -> bool:
        """Login and get JWT token."""
        if not self.email_address or not self.password:
            return False
        
        try:
            resp = self.http_client.post(
                f"{self.BASE_URL}/token",
                json={
                    "address": self.email_address,
                    "password": self.password
                }
            )
            
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get('token')
                return True
            else:
                logger.error(f"Login failed: {resp.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers with auth token."""
        return {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json',
        }
    
    def get_messages(self, page: int = 1) -> List[Dict]:
        """Get inbox messages.
        
        Returns:
            List of message objects with id, from, subject, etc.
        """
        if not self.token:
            if not self._login():
                return []
        
        try:
            resp = self.http_client.get(
                f"{self.BASE_URL}/messages",
                headers=self._get_auth_headers(),
                params={'page': page}
            )
            
            if resp.status_code == 200:
                data = resp.json()
                # Handle paginated response
                if isinstance(data, dict) and 'hydra:member' in data:
                    return data['hydra:member']
                return data if isinstance(data, list) else []
            else:
                logger.warning(f"Get messages failed: {resp.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []
    
    def get_message_content(self, message_id: str) -> Optional[Dict]:
        """Get full message content.
        
        Args:
            message_id: Message ID
            
        Returns:
            Message object with full content
        """
        if not self.token:
            if not self._login():
                return None
        
        try:
            resp = self.http_client.get(
                f"{self.BASE_URL}/messages/{message_id}",
                headers=self._get_auth_headers()
            )
            
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning(f"Get message content failed: {resp.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting message content: {e}")
            return None
    
    def wait_for_sheerid_email(self, verification_id: str = None, 
                               max_wait: int = 120, 
                               poll_interval: int = 5) -> Optional[str]:
        """Wait for SheerID verification email and extract token.
        
        Args:
            verification_id: Optional verification ID to match
            max_wait: Maximum seconds to wait
            poll_interval: Seconds between checks
            
        Returns:
            Email token if found, None otherwise
        """
        self._log("EMAIL", f"Waiting for SheerID email at {self.email_address}...")
        
        attempts = max_wait // poll_interval
        seen_ids = set()
        
        for i in range(attempts):
            messages = self.get_messages()
            
            for msg in messages:
                msg_id = msg.get('id')
                
                # Skip already seen messages
                if msg_id in seen_ids:
                    continue
                seen_ids.add(msg_id)
                
                subject = msg.get('subject', '')
                sender = msg.get('from', {})
                sender_address = sender.get('address', '') if isinstance(sender, dict) else str(sender)
                
                self._log("EMAIL", f"New email: {subject[:40]}...")
                
                # Check if SheerID email
                if self._is_sheerid_email(subject, sender_address):
                    self._log("EMAIL", "Found SheerID email!")
                    
                    # Get full content
                    full_msg = self.get_message_content(msg_id)
                    if full_msg:
                        token = self._extract_verification_token(full_msg, verification_id)
                        if token:
                            self._log("TOKEN", f"Extracted token: {token}")
                            return token
            
            # Wait before next poll
            remaining = (attempts - i - 1) * poll_interval
            self._log("WAIT", f"Polling inbox... ({remaining}s remaining)")
            time.sleep(poll_interval)
        
        self._log("ERROR", "SheerID email not received in time")
        return None
    
    def _is_sheerid_email(self, subject: str, sender: str) -> bool:
        """Check if email is from SheerID."""
        sheerid_indicators = [
            'sheerid' in subject.lower(),
            'sheerid' in sender.lower(),
            'verify' in subject.lower() and 'email' in subject.lower(),
            'verification' in subject.lower(),
            'almost there' in subject.lower(),
            'confirm your email' in subject.lower(),
        ]
        return any(sheerid_indicators)
    
    def _extract_verification_token(self, message: Dict, verification_id: str = None) -> Optional[str]:
        """Extract verification token from SheerID email.
        
        Args:
            message: Full message object
            verification_id: Optional verification ID to match
            
        Returns:
            Token string if found
        """
        # Get email content (HTML or text)
        html_content = message.get('html', [''])[0] if message.get('html') else ''
        text_content = message.get('text', '')
        content = html_content or text_content
        
        if not content:
            return None
        
        # Pattern 1: Direct emailToken parameter
        # https://services.sheerid.com/verify/PROGRAM_ID/?verificationId=XXX&emailToken=123456
        token_patterns = [
            r'emailToken=(\d{6,})',
            r'emailToken=(\d+)',
            r'token=(\d{6,})',
            r'verificationToken=(\d+)',
        ]
        
        for pattern in token_patterns:
            match = re.search(pattern, content)
            if match:
                token = match.group(1)
                # Validate - should be 6 digits
                if len(token) >= 6:
                    return token
        
        # Pattern 2: Full verification URL
        url_pattern = r'https://services\.sheerid\.com/verify/[^\s"\'<>]+'
        url_match = re.search(url_pattern, content)
        
        if url_match:
            url = url_match.group(0)
            self._log("DEBUG", f"Found SheerID URL: {url[:80]}...")
            
            # Extract token from URL
            for pattern in token_patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
        
        # Pattern 3: 6-digit code in email body (common for email verification)
        code_pattern = r'\b(\d{6})\b'
        codes = re.findall(code_pattern, content)
        
        if codes:
            # Return last 6-digit code (usually the verification code)
            return codes[-1]
        
        return None
    
    def delete_account(self) -> bool:
        """Delete the temporary email account."""
        if not self.token or not self.account_id:
            return False
        
        try:
            resp = self.http_client.delete(
                f"{self.BASE_URL}/accounts/{self.account_id}",
                headers=self._get_auth_headers()
            )
            return resp.status_code == 204
        except:
            return False
    
    def close(self):
        """Close HTTP client."""
        if self.http_client:
            self.http_client.close()


def create_temp_email(status_callback=None) -> Tuple[MailTmClient, str]:
    """Helper function to quickly create a temporary email.
    
    Returns:
        Tuple of (client, email_address) or (None, None) on failure
    """
    client = MailTmClient(status_callback=status_callback)
    email, _ = client.create_account()
    
    if email:
        return client, email
    return None, None


def test_mail_tm():
    """Test Mail.tm API."""
    print("=" * 50)
    print("Testing Mail.tm API")
    print("=" * 50)
    
    def status(step, msg):
        print(f"[{step}] {msg}")
    
    client = MailTmClient(status_callback=status)
    
    # Test 1: Get domains
    print("\n1. Getting available domains...")
    domains = client.get_domains()
    print(f"   Found {len(domains)} domains: {domains[:3]}...")
    
    if not domains:
        print("   FAILED - No domains available")
        return
    
    # Test 2: Create account
    print("\n2. Creating temporary email...")
    email, password = client.create_account()
    
    if email:
        print(f"   SUCCESS: {email}")
    else:
        print("   FAILED - Could not create account")
        return
    
    # Test 3: Check inbox
    print("\n3. Checking inbox...")
    messages = client.get_messages()
    print(f"   Found {len(messages)} messages")
    
    # Test 4: Wait a bit then cleanup
    print("\n4. Cleanup...")
    client.close()
    print("   Done!")
    
    print("\n" + "=" * 50)
    print(f"Email created: {email}")
    print("You can use this email for SheerID verification!")
    print("=" * 50)


if __name__ == "__main__":
    test_mail_tm()
