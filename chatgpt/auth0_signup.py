"""
ChatGPT Auth0 Signup - API-based approach
Reverse engineered from ChatGPT authentication flow

Based on analysis:
- Auth0 Domain: auth.openai.com
- Client ID: varies (web app uses different IDs)
- Redirect URI: https://chatgpt.com/api/auth/callback/openai
"""
import json
import random
import string
import hashlib
import base64
import secrets
from typing import Dict, Optional, Tuple
import urllib.parse

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    import requests

# Import from utils
from utils import load_config, get_proxy_url


def generate_code_verifier() -> str:
    """Generate PKCE code verifier."""
    return secrets.token_urlsafe(32)


def generate_code_challenge(verifier: str) -> str:
    """Generate PKCE code challenge from verifier."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip('=')


def generate_state() -> str:
    """Generate random state parameter."""
    return secrets.token_urlsafe(24)


def generate_random_email() -> str:
    """Generate random email for testing."""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"testuser_{random_str}@gmail.com"


class Auth0SignupClient:
    """Auth0 client for ChatGPT signup."""
    
    # Auth0 configuration (from reverse engineering)
    AUTH0_DOMAIN = "auth.openai.com"
    CLIENT_ID = "pdlLIX2Y72MIl2rhLhTE9VV9bN905kBh"  # ChatGPT web client ID
    REDIRECT_URI = "https://chatgpt.com/api/auth/callback/openai"
    AUDIENCE = "https://api.openai.com/v1"
    
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.proxies = None
        if proxy:
            self.proxies = {
                "http://": f"http://{proxy}",
                "https://": f"http://{proxy}"
            }
            print(f"[INFO] Using proxy: {proxy[:30]}...")
        
        # Session with cookies
        if HAS_HTTPX:
            if proxy:
                transport = httpx.HTTPTransport(proxy=f"http://{proxy}")
                self.client = httpx.Client(
                    transport=transport,
                    timeout=30.0,
                    follow_redirects=True
                )
            else:
                self.client = httpx.Client(
                    timeout=30.0,
                    follow_redirects=True
                )
        else:
            self.client = requests.Session()
            if proxy:
                self.client.proxies = {
                    'http': f'http://{proxy}',
                    'https': f'http://{proxy}'
                }
        
        # PKCE
        self.code_verifier = generate_code_verifier()
        self.code_challenge = generate_code_challenge(self.code_verifier)
        self.state = generate_state()
    
    def _request(self, method: str, url: str, **kwargs) -> Tuple[int, Dict]:
        """Make HTTP request."""
        try:
            if HAS_HTTPX:
                resp = self.client.request(method, url, **kwargs)
            else:
                resp = self.client.request(method, url, **kwargs)
            
            try:
                return resp.status_code, resp.json()
            except:
                return resp.status_code, {"text": resp.text[:500]}
        except Exception as e:
            return 0, {"error": str(e)}
    
    def step1_get_authorize_url(self) -> str:
        """Build Auth0 authorization URL."""
        params = {
            "client_id": self.CLIENT_ID,
            "audience": self.AUDIENCE,
            "redirect_uri": self.REDIRECT_URI,
            "scope": "openid profile email offline_access",
            "response_type": "code",
            "response_mode": "query",
            "state": self.state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": "S256",
            "prompt": "login",
            "screen_hint": "signup",
        }
        
        url = f"https://{self.AUTH0_DOMAIN}/authorize?" + urllib.parse.urlencode(params)
        return url
    
    def step2_initiate_auth(self) -> Dict:
        """Step 2: Start authorization flow."""
        print("[STEP 1] Getting authorization page...")
        
        auth_url = self.step1_get_authorize_url()
        print(f"   Auth URL: {auth_url[:80]}...")
        
        status, data = self._request("GET", auth_url)
        print(f"   Status: {status}")
        
        return {"status": status, "data": data}
    
    def step3_signup(self, email: str, password: str) -> Dict:
        """Step 3: Submit signup form to Auth0."""
        print(f"\n[STEP 2] Signing up: {email}")
        
        signup_url = f"https://{self.AUTH0_DOMAIN}/dbconnections/signup"
        
        payload = {
            "client_id": self.CLIENT_ID,
            "email": email,
            "password": password,
            "connection": "Username-Password-Authentication",
        }
        
        headers = {
            "Content-Type": "application/json",
            "Origin": f"https://{self.AUTH0_DOMAIN}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
        }
        
        status, data = self._request("POST", signup_url, json=payload, headers=headers)
        print(f"   Status: {status}")
        print(f"   Response: {data}")
        
        return {"status": status, "data": data}
    
    def test_signup(self, email: str = None, password: str = None) -> Dict:
        """Test the full signup flow."""
        email = email or generate_random_email()
        password = password or "TestPass123!@#"
        
        print("=" * 60)
        print("  CHATGPT AUTH0 SIGNUP TEST")
        print("=" * 60)
        print(f"  Email: {email}")
        print(f"  Auth0 Domain: {self.AUTH0_DOMAIN}")
        print(f"  Client ID: {self.CLIENT_ID[:20]}...")
        print("=" * 60)
        
        # Step 1: Get auth page
        result1 = self.step2_initiate_auth()
        
        # Step 2: Try signup
        result2 = self.step3_signup(email, password)
        
        print()
        print("=" * 60)
        print("  RESULTS")
        print("=" * 60)
        
        if result2.get("status") == 200:
            print("  ✅ Signup API returned 200!")
        else:
            print(f"  ❌ Signup failed: {result2.get('status')}")
            print(f"     {result2.get('data')}")
        
        return {
            "auth_result": result1,
            "signup_result": result2
        }


def main():
    print("\n🔬 Testing ChatGPT Auth0 API-based Signup\n")
    
    # Load proxy from config
    config = load_config()
    proxy = get_proxy_url(config)
    
    # Create client
    client = Auth0SignupClient(proxy=proxy)
    
    # Test signup
    result = client.test_signup()
    
    print("\n[DEBUG] Full result:")
    print(json.dumps(result, indent=2, default=str)[:1000])


if __name__ == "__main__":
    main()
