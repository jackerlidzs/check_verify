"""
IMAP Email Client for SheerID Verification
Auto-reads verification emails and extracts tokens
"""
import imaplib
import email
import re
import time
import json
from pathlib import Path
from email.header import decode_header
from typing import Optional, List, Dict


class EmailClient:
    """IMAP email client for reading SheerID verification emails."""
    
    def __init__(self, config: dict):
        """Initialize email client with config.
        
        Config format:
        {
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
            "email_address": "your@email.com",
            "email_password": "your_app_password",
            "use_ssl": true
        }
        """
        self.server = config.get('imap_server', 'imap.gmail.com')
        self.port = config.get('imap_port', 993)
        self.email = config.get('email_address', '')
        self.password = config.get('email_password', '')
        self.use_ssl = config.get('use_ssl', True)
        self.connection = None
    
    def connect(self) -> bool:
        """Connect to IMAP server."""
        try:
            if self.use_ssl:
                self.connection = imaplib.IMAP4_SSL(self.server, self.port)
            else:
                self.connection = imaplib.IMAP4(self.server, self.port)
            
            self.connection.login(self.email, self.password)
            return True
        except Exception as e:
            print(f"[ERROR] Email connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server."""
        if self.connection:
            try:
                self.connection.logout()
            except:
                pass
            self.connection = None
    
    def get_latest_emails(self, count: int = 5) -> List[Dict]:
        """Get latest emails from inbox."""
        emails = []
        
        try:
            self.connection.select('INBOX')
            
            # Search for all emails
            status, messages = self.connection.search(None, 'ALL')
            message_ids = messages[0].split()
            
            # Get latest N emails
            latest_ids = message_ids[-count:] if len(message_ids) >= count else message_ids
            
            for msg_id in reversed(latest_ids):
                status, msg_data = self.connection.fetch(msg_id, '(RFC822)')
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Decode subject
                        subject = decode_header(msg['Subject'])[0][0]
                        if isinstance(subject, bytes):
                            subject = subject.decode()
                        
                        # Get sender
                        sender = msg['From']
                        
                        # Get body
                        body = self._get_body(msg)
                        
                        emails.append({
                            'subject': subject or '',
                            'from': sender or '',
                            'content': body
                        })
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch emails: {e}")
        
        return emails
    
    def _get_body(self, msg) -> str:
        """Extract body from email message."""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    try:
                        body = part.get_payload(decode=True).decode()
                        break
                    except:
                        pass
                elif content_type == 'text/html':
                    try:
                        body = part.get_payload(decode=True).decode()
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode()
            except:
                body = str(msg.get_payload())
        
        return body
    
    def find_sheerid_token(self, verification_id: str, max_wait: int = 60) -> Optional[str]:
        """Wait and find SheerID verification token in emails.
        
        Args:
            verification_id: The SheerID verification ID to look for
            max_wait: Maximum seconds to wait
            
        Returns:
            Email token if found, None otherwise
        """
        print(f"   -> Waiting for verification email...")
        
        attempts = max_wait // 3  # Check every 3 seconds
        
        for i in range(attempts):
            emails = self.get_latest_emails(10)
            
            for e in emails:
                content = e.get('content', '')
                subject = e.get('subject', '')
                
                # Check if this is SheerID email
                if 'sheerid' in subject.lower() or 'verify' in subject.lower() or \
                   "You're almost there" in content or "Finish Verifying" in content:
                    
                    # Look for token URL
                    pattern = rf"https://services\.sheerid\.com/verify/[^\s\"'<>]*emailToken=(\d+)"
                    match = re.search(pattern, content)
                    
                    if match and verification_id in content:
                        token = match.group(1)
                        print(f"   [OK] Found email token: {token}")
                        return token
            
            print(f"      Waiting... ({i+1}/{attempts})")
            time.sleep(3)
        
        print("   [ERROR] Email not received in time")
        return None


def load_email_config() -> dict:
    """Load email configuration from config file."""
    config_paths = [
        Path('config/military.json'),
        Path('config/email.json'),
        Path('military/config/email.json'),
        Path('config.json'),
    ]
    
    for path in config_paths:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    config = json.load(f)
                if 'email' in config:
                    return config['email']
                elif 'imap_server' in config:
                    return config
            except:
                pass
    
    return {}


def test_connection():
    """Test email connection."""
    config = load_email_config()
    
    if not config:
        print("No email configuration found!")
        print("Please create config/email.json with:")
        print(json.dumps({
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
            "email_address": "your@email.com",
            "email_password": "your_app_password",
            "use_ssl": True
        }, indent=2))
        return
    
    print(f"Testing connection to {config.get('imap_server')}...")
    
    client = EmailClient(config)
    
    if client.connect():
        print("[OK] Connected successfully!")
        
        emails = client.get_latest_emails(3)
        print(f"Found {len(emails)} recent emails")
        
        for e in emails:
            print(f"  - {e['subject'][:50]}...")
        
        client.disconnect()
    else:
        print("[ERROR] Connection failed!")


if __name__ == "__main__":
    test_connection()
