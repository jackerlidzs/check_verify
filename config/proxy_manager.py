"""Proxy Manager - Multi-Provider Support

Supports multiple proxy providers:
- Bright Data (residential)
- DataImpulse (residential)
- Qv2ray (SOCKS5 local)
- None (direct connection)

Shows IP with country flag when proxy enabled, nothing when disabled.
"""

import json
import httpx
from pathlib import Path
from typing import Optional, Dict, Tuple

# Config path
CONFIG_DIR = Path(__file__).parent
PROXY_CONFIG_FILE = CONFIG_DIR / "proxy.json"

# Country code to flag emoji mapping
COUNTRY_FLAGS = {
    "us": "🇺🇸", "uk": "🇬🇧", "gb": "🇬🇧", "ca": "🇨🇦", "au": "🇦🇺",
    "de": "🇩🇪", "fr": "🇫🇷", "jp": "🇯🇵", "kr": "🇰🇷", "br": "🇧🇷",
    "mx": "🇲🇽", "in": "🇮🇳", "it": "🇮🇹", "es": "🇪🇸", "nl": "🇳🇱",
    "sg": "🇸🇬", "hk": "🇭🇰", "tw": "🇹🇼", "th": "🇹🇭", "vn": "🇻🇳",
}


class ProxyManager:
    """Manages multi-provider proxy configuration."""
    
    def __init__(self, config_path: Path = None):
        self.config_path = config_path or PROXY_CONFIG_FILE
        self.config = self._load_config()
        self._current_ip = None
        self._country = None
    
    def _load_config(self) -> Dict:
        """Load proxy config from JSON file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"active_provider": "none", "providers": {"none": {"type": "direct"}}}
    
    @property
    def active_provider_name(self) -> str:
        """Get active provider name."""
        return self.config.get("active_provider", "none")
    
    @property
    def active_provider(self) -> Dict:
        """Get active provider config."""
        name = self.active_provider_name
        providers = self.config.get("providers", {})
        return providers.get(name, {"type": "direct"})
    
    @property
    def enabled(self) -> bool:
        """Check if proxy is enabled (not 'none' or 'direct')."""
        provider = self.active_provider
        return provider.get("type") not in ["direct", None] and self.active_provider_name != "none"
    
    @property
    def proxy_url(self) -> Optional[str]:
        """Get proxy URL for httpx."""
        if not self.enabled:
            return None
        
        provider = self.active_provider
        protocol = provider.get("protocol", "http")
        host = provider.get("host", "")
        
        # Get port (sticky_port for DataImpulse, port otherwise)
        port = provider.get("port") or provider.get("sticky_port", "")
        
        username = provider.get("username", "")
        password = provider.get("password", "")
        
        if username and password:
            return f"{protocol}://{username}:{password}@{host}:{port}"
        else:
            return f"{protocol}://{host}:{port}"
    
    def get_country_flag(self, country_code: str = None) -> str:
        """Get flag emoji for country code."""
        code = country_code or self.active_provider.get("country", "")
        if code:
            code = code.lower()
        return COUNTRY_FLAGS.get(code, "🌐")
    
    def detect_ip(self) -> Tuple[Optional[str], Optional[str]]:
        """Detect current IP and country."""
        try:
            with httpx.Client(proxy=self.proxy_url, timeout=15, verify=False) as client:
                response = client.get("https://ipinfo.io/json")
                if response.status_code == 200:
                    data = response.json()
                    self._current_ip = data.get("ip")
                    self._country = data.get("country", "").lower()
                    return self._current_ip, self._country
        except Exception as e:
            print(f"IP detection error: {e}")
        
        return None, None
    
    def get_ip_display(self) -> Optional[str]:
        """Get formatted IP display string with flag.
        
        Returns:
            "🇺🇸 192.168.1.1" if proxy enabled and IP detected
            None if proxy disabled or detection failed
        """
        if not self.enabled:
            return None
        
        ip, country = self.detect_ip()
        if ip:
            flag = self.get_country_flag(country)
            return f"{flag} {ip}"
        
        # Fallback: use configured country
        flag = self.get_country_flag()
        return f"{flag} (connecting...)"
    
    def get_provider_info(self) -> str:
        """Get provider info string."""
        if not self.enabled:
            return "Direct (No Proxy)"
        
        provider = self.active_provider
        name = provider.get("name", self.active_provider_name)
        return name
    
    def set_provider(self, provider_name: str) -> bool:
        """Switch to a different provider."""
        providers = self.config.get("providers", {})
        if provider_name in providers:
            self.config["active_provider"] = provider_name
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            return True
        return False
    
    def list_providers(self) -> Dict[str, str]:
        """List all available providers."""
        providers = self.config.get("providers", {})
        return {k: v.get("name", k) for k, v in providers.items()}


# Global instance
_proxy_manager = None

def get_proxy_manager() -> ProxyManager:
    """Get or create global proxy manager."""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager


def get_proxy_url() -> Optional[str]:
    """Get proxy URL for httpx client."""
    return get_proxy_manager().proxy_url


def get_ip_display() -> Optional[str]:
    """Get IP display with flag (or None if proxy disabled)."""
    return get_proxy_manager().get_ip_display()


def get_proxy_config() -> Optional[Dict]:
    """Get proxy config for Playwright browser.
    
    Returns dict with:
        enabled: bool
        host: str
        port: int
        username: str
        password: str
    """
    pm = get_proxy_manager()
    if not pm.enabled:
        return None
    
    provider = pm.active_provider
    return {
        "enabled": True,
        "host": provider.get("host", ""),
        "port": provider.get("port") or provider.get("sticky_port", 0),
        "username": provider.get("username", ""),
        "password": provider.get("password", ""),
    }


if __name__ == "__main__":
    # Test proxy
    pm = ProxyManager()
    
    print("=" * 50)
    print("Proxy Configuration")
    print("=" * 50)
    
    print(f"\nAvailable providers:")
    for key, name in pm.list_providers().items():
        active = " [ACTIVE]" if key == pm.active_provider_name else ""
        print(f"  - {key}: {name}{active}")
    
    print(f"\nActive: {pm.active_provider_name}")
    print(f"Enabled: {pm.enabled}")
    print(f"Provider: {pm.get_provider_info()}")
    
    if pm.enabled:
        print(f"Proxy URL: {pm.proxy_url[:60]}...")
        print("\nDetecting IP...")
        display = pm.get_ip_display()
        print(f"Result: {display}")
    else:
        print("\nNo proxy configured (direct connection)")
