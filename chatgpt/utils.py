"""
ChatGPT Module - Shared Utilities
Common functions used across scripts to reduce code duplication.
"""
import json
import random
import string
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)
CONFIG_FILE = BASE_DIR / "config.json"

# Default config template
DEFAULT_CONFIG = {
    "telegram": {
        "api_id": "",
        "api_hash": "",
        "bot_username": "TempMail_org_bot",
        "session_file": "data/telegram_session"
    },
    "proxy": {
        "enabled": False,
        "type": "isp",
        "host": "",
        "port": 8080,
        "username": "",
        "password": ""
    },
    "signup": {
        "password_length": 14,
        "headless": False,
        "timeout": 60000
    }
}


def load_config() -> Dict[str, Any]:
    """Load config from config.json file with validation."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate required fields
            errors = validate_config(config)
            if errors:
                print("⚠️ Config validation warnings:")
                for error in errors:
                    print(f"   - {error}")
            
            return config
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in config.json: {e}")
            return DEFAULT_CONFIG
    else:
        print("⚠️ config.json not found, using defaults")
        print("   Copy config.example.json to config.json and fill in your credentials")
        return DEFAULT_CONFIG


def validate_config(config: Dict) -> list:
    """Validate config and return list of errors/warnings."""
    errors = []
    
    # Check telegram section
    telegram = config.get("telegram", {})
    if not telegram.get("api_id"):
        errors.append("telegram.api_id is missing or empty")
    if not telegram.get("api_hash"):
        errors.append("telegram.api_hash is missing or empty")
    
    # Check proxy section if enabled
    proxy = config.get("proxy", {})
    if proxy.get("enabled"):
        if not proxy.get("host"):
            errors.append("proxy.host is missing but proxy is enabled")
        if not proxy.get("port"):
            errors.append("proxy.port is missing but proxy is enabled")
    
    return errors


def generate_password(length: int = 14) -> str:
    """Generate a random secure password."""
    chars = string.ascii_letters + string.digits + "!@#$%"
    password = ''.join(random.choice(chars) for _ in range(length))
    return password


def save_account(email: str, password: str, access_token: Optional[str] = None) -> None:
    """Save created account to accounts.json."""
    if ACCOUNTS_FILE.exists():
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            accounts = json.load(f)
    else:
        accounts = {"accounts": []}
    
    accounts["accounts"].append({
        "email": email,
        "password": password,
        "access_token": access_token,
        "created_at": datetime.now().isoformat(),
        "status": "active"
    })
    
    with open(ACCOUNTS_FILE, "w", encoding='utf-8') as f:
        json.dump(accounts, f, indent=2)
    
    print(f"  💾 Account saved to {ACCOUNTS_FILE}")


def get_accounts() -> list:
    """Get list of all saved accounts."""
    if ACCOUNTS_FILE.exists():
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("accounts", [])
    return []


def get_proxy_config(config: Dict) -> Optional[Dict]:
    """Get playwright-compatible proxy config from config dict."""
    proxy_cfg = config.get('proxy', {})
    if not proxy_cfg.get('enabled'):
        return None
    
    host = proxy_cfg.get('host')
    port = proxy_cfg.get('port')
    if not host or not port:
        return None
    
    proxy = {
        "server": f"http://{host}:{port}",
    }
    
    username = proxy_cfg.get('username')
    password = proxy_cfg.get('password')
    if username:
        proxy["username"] = username
    if password:
        proxy["password"] = password
    
    return proxy


def get_proxy_url(config: Dict) -> Optional[str]:
    """Get proxy URL string for httpx/requests."""
    proxy_cfg = config.get('proxy', {})
    if not proxy_cfg.get('enabled'):
        return None
    
    host = proxy_cfg.get('host')
    port = proxy_cfg.get('port')
    if not host or not port:
        return None
    
    username = proxy_cfg.get('username')
    password = proxy_cfg.get('password')
    
    if username and password:
        return f"{username}:{password}@{host}:{port}"
    return f"{host}:{port}"


def get_session_path(config: Dict) -> Path:
    """Get telegram session file path from config."""
    session_file = config.get("telegram", {}).get("session_file", "data/telegram_session")
    return BASE_DIR / session_file
