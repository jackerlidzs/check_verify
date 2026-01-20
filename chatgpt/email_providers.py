"""
Email Providers for ChatGPT Signup
Supports:
- Telegram Bot (TempMail_org_bot)
- Smailpro API (RapidAPI)
"""
import re
import time
import asyncio
import random
import string
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class BaseEmailProvider(ABC):
    """Abstract base class for email providers."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the email service."""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from the email service."""
        pass
    
    @abstractmethod
    async def get_new_email(self) -> Optional[str]:
        """Get a new temp email address."""
        pass
    
    @abstractmethod
    async def wait_for_verification(self, timeout: int = 180) -> Optional[Dict]:
        """Wait for verification email and extract code/link."""
        pass
    
    @abstractmethod
    async def delete_email(self, email: str):
        """Delete/cleanup an email address."""
        pass
    
    async def get_email_list(self) -> list:
        """Get list of current emails (if supported)."""
        return []
    
    async def cleanup_all_emails(self):
        """Cleanup all emails (if supported)."""
        pass


class TelegramEmailProvider(BaseEmailProvider):
    """Telegram bot email provider using @TempMail_org_bot."""
    
    def __init__(self, api_id: str, api_hash: str, session_file: str, bot_username: str = "TempMail_org_bot"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_file = session_file
        self.bot_username = bot_username
        self.client = None
        self.current_email = None
    
    async def connect(self) -> bool:
        from telethon import TelegramClient
        self.client = TelegramClient(str(self.session_file), self.api_id, self.api_hash)
        await self.client.start()
        me = await self.client.get_me()
        print(f"  ✅ Telegram connected as @{me.username}")
        return True
    
    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
    
    async def get_new_email(self) -> Optional[str]:
        """Get a new temp email address from @TempMail_org_bot."""
        print("  📧 Requesting new email from @TempMail_org_bot...")
        
        await self.client.send_message(self.bot_username, "/new")
        await asyncio.sleep(4)
        
        async for msg in self.client.iter_messages(self.bot_username, limit=5):
            if msg.text:
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg.text)
                if email_match:
                    email = email_match.group()
                    self.current_email = email
                    print(f"  ✅ Got email: {email}")
                    return email
        
        print("  ⚠️ Trying /start...")
        await self.client.send_message(self.bot_username, "/start")
        await asyncio.sleep(4)
        
        async for msg in self.client.iter_messages(self.bot_username, limit=5):
            if msg.text:
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg.text)
                if email_match:
                    email = email_match.group()
                    self.current_email = email
                    print(f"  ✅ Got email: {email}")
                    return email
        
        print("  ❌ Failed to get email")
        return None
    
    async def get_email_list(self) -> list:
        await self.client.send_message(self.bot_username, "/list")
        await asyncio.sleep(3)
        
        emails = []
        async for msg in self.client.iter_messages(self.bot_username, limit=5):
            if msg.text:
                matches = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', msg.text)
                emails.extend(matches)
        return list(set(emails))
    
    async def delete_email(self, email: str):
        print(f"  🗑️ Deleting: {email}")
        await self.client.send_message(self.bot_username, f"/delete {email}")
        await asyncio.sleep(2)
    
    async def cleanup_all_emails(self):
        print("  🧹 Cleaning all emails...")
        emails = await self.get_email_list()
        for email in emails:
            await self.delete_email(email)
            await asyncio.sleep(1)
    
    async def wait_for_verification(self, timeout: int = 180) -> Optional[Dict]:
        print(f"  ⏳ Waiting for verification (max {timeout}s)...")
        start = time.time()
        checked_ids = set()
        
        while time.time() - start < timeout:
            async for msg in self.client.iter_messages(self.bot_username, limit=20):
                if msg.id in checked_ids:
                    continue
                checked_ids.add(msg.id)
                
                if msg.text:
                    text_lower = msg.text.lower()
                    
                    if any(x in text_lower for x in ["openai", "chatgpt", "verify", "verification", "code"]):
                        code_match = re.search(r'\b(\d{6})\b', msg.text)
                        if code_match:
                            code = code_match.group(1)
                            print(f"  ✅ Found code: {code}")
                            return {"type": "code", "value": code}
                        
                        link_match = re.search(r'https://[^\s<>"]+', msg.text)
                        if link_match:
                            link = link_match.group()
                            print(f"  ✅ Found link: {link[:60]}...")
                            return {"type": "link", "value": link}
            
            elapsed = int(time.time() - start)
            if elapsed % 30 == 0 and elapsed > 0:
                print(f"  ⏳ Still waiting... ({elapsed}s)")
            await asyncio.sleep(5)
        
        print("  ❌ Verification timeout")
        return None


class SmailproEmailProvider(BaseEmailProvider):
    """Smailpro API email provider via RapidAPI - supports real-looking domains."""
    
    BASE_URL = "https://temporary-email-api-by-sonjj.p.rapidapi.com"
    
    def __init__(self, rapidapi_key: str, preferred_domain: Optional[str] = None):
        self.rapidapi_key = rapidapi_key
        self.preferred_domain = preferred_domain
        self.available_domains = []
        self.current_email = None
        self.client = None
    
    async def connect(self) -> bool:
        """Initialize connection and fetch available domains."""
        print("  🔐 Connecting to Smailpro API...")
        
        if not HAS_HTTPX:
            raise ImportError("httpx is required. Install with: pip install httpx")
        
        self.client = httpx.AsyncClient(timeout=30.0)
        
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/domains",
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                self.available_domains = data.get("domains", [])
                print(f"  ✅ Smailpro connected ({len(self.available_domains)} domains)")
                return True
            else:
                print(f"  ❌ Failed to fetch domains: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ❌ Smailpro connection error: {e}")
            return False
    
    async def disconnect(self):
        if self.client:
            await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "x-rapidapi-host": "temporary-email-api-by-sonjj.p.rapidapi.com",
            "x-rapidapi-key": self.rapidapi_key,
            "Accept": "application/json"
        }
    
    def _select_best_domain(self) -> Optional[str]:
        """Select domain with priority: .edu > known working > random."""
        if self.preferred_domain:
            return self.preferred_domain
        
        if not self.available_domains:
            return None
        
        # Priority 1: .edu domains (higher acceptance rate)
        edu_domains = [d for d in self.available_domains if '.edu' in d.lower()]
        if edu_domains:
            domain = random.choice(edu_domains)
            print(f"  🎓 Using edu domain: {domain}")
            return domain
        
        # Priority 2: Known working domains with ChatGPT
        working_domains = ["ewebrus.com", "odeask.com", "thewite.com", "drewzen.com", "ofanda.com"]
        available_working = [d for d in self.available_domains if d.strip() in working_domains]
        if available_working:
            domain = random.choice(available_working)
            print(f"  ✅ Using verified domain: {domain}")
            return domain
        
        # Fallback: random from available
        return random.choice(self.available_domains)
    
    async def get_new_email(self) -> Optional[str]:
        """Create a new temp email address."""
        print("  📧 Generating new email from Smailpro...")
        
        # Select best domain
        domain = self._select_best_domain()
        
        if not domain:
            print("  ❌ No domains available")
            return None
        
        # Generate random prefix
        prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        email = f"{prefix}@{domain.strip()}"
        
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/create",
                params={"email": email},
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                self.current_email = data.get("email", email)
                print(f"  ✅ Created email: {self.current_email}")
                return self.current_email
            else:
                print(f"  ❌ Failed to create email: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"  ❌ Email creation error: {e}")
            return None
    
    async def wait_for_verification(self, timeout: int = 180) -> Optional[Dict]:
        """Poll inbox for verification email."""
        if not self.current_email:
            print("  ❌ No email address set")
            return None
        
        print(f"  ⏳ Waiting for verification at {self.current_email} (max {timeout}s)...")
        start = time.time()
        checked_ids = set()
        
        while time.time() - start < timeout:
            try:
                response = await self.client.get(
                    f"{self.BASE_URL}/inbox",
                    params={"email": self.current_email},
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    messages = data.get("messages", [])
                    
                    for msg in messages:
                        msg_id = msg.get("mid")
                        if not msg_id or msg_id in checked_ids:
                            continue
                        checked_ids.add(msg_id)
                        
                        subject = str(msg.get("textSubject", "")).lower()
                        from_addr = str(msg.get("textFrom", "")).lower()
                        
                        if any(x in subject or x in from_addr for x in ["openai", "chatgpt", "verify", "noreply"]):
                            print(f"  📬 Found email: {subject[:50]}")
                            
                            content = await self._get_message_content(msg_id)
                            if content:
                                code_match = re.search(r'\b(\d{6})\b', content)
                                if code_match:
                                    code = code_match.group(1)
                                    print(f"  ✅ Found verification code: {code}")
                                    return {"type": "code", "value": code}
                                
                                link_match = re.search(r'https://[^\s<>"\']+verify[^\s<>"\']*', content, re.IGNORECASE)
                                if not link_match:
                                    link_match = re.search(r'https://[^\s<>"\']+', content)
                                if link_match:
                                    link = link_match.group()
                                    print(f"  ✅ Found link: {link[:60]}...")
                                    return {"type": "link", "value": link}
                
            except Exception as e:
                print(f"  ⚠️ Inbox check error: {e}")
            
            elapsed = int(time.time() - start)
            if elapsed % 30 == 0 and elapsed > 0:
                print(f"  ⏳ Still waiting... ({elapsed}s)")
            await asyncio.sleep(5)
        
        print("  ❌ Verification timeout")
        return None
    
    async def _get_message_content(self, message_id: str) -> Optional[str]:
        """Get full content of a message."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/message",
                params={"email": self.current_email, "mid": message_id},
                headers=self._get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("body", "")
        except Exception as e:
            print(f"  ⚠️ Failed to get message: {e}")
        return None
    
    async def delete_email(self, email: str):
        """Delete email (set expiry to -1)."""
        print(f"  🗑️ Deleting: {email}")
        try:
            await self.client.get(
                f"{self.BASE_URL}/create",
                params={"email": email, "expiry_minutes": -1},
                headers=self._get_headers()
            )
        except:
            pass


def get_email_provider(config: Dict[str, Any]) -> BaseEmailProvider:
    """Factory function to get the appropriate email provider based on config."""
    
    email_config = config.get("email_provider", {})
    provider_type = email_config.get("type", "smailpro").lower()
    
    print(f"  📧 Using email provider: {provider_type}")
    
    if provider_type == "smailpro":
        smailpro_config = email_config.get("smailpro", {})
        rapidapi_key = smailpro_config.get("rapidapi_key", "")
        domain = smailpro_config.get("domain")
        
        if not rapidapi_key:
            raise ValueError("Smailpro RapidAPI key required. Set email_provider.smailpro.rapidapi_key in config.json")
        
        return SmailproEmailProvider(rapidapi_key, domain)
    
    else:  # telegram
        telegram_config = config.get("telegram", {})
        
        api_id = telegram_config.get("api_id", "")
        api_hash = telegram_config.get("api_hash", "")
        session_file = telegram_config.get("session_file", "data/telegram_session")
        bot_username = telegram_config.get("bot_username", "TempMail_org_bot")
        
        if not api_id or not api_hash:
            raise ValueError("Telegram API credentials required. Set telegram.api_id and telegram.api_hash in config.json")
        
        from pathlib import Path
        base_dir = Path(__file__).parent
        session_path = base_dir / session_file
        
        return TelegramEmailProvider(api_id, api_hash, str(session_path), bot_username)
