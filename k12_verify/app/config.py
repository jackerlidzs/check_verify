"""
Application Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DOC_TEMPLATES_DIR = BASE_DIR / "doc_templates"

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/k12_verify.db")

# Playwright
PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Districts
DISTRICTS = {
    "nyc_doe": {
        "name": "New York City Department of Education",
        "abbreviation": "NYC DOE",
        "ee_id_digits": 7
    },
    "miami_dade": {
        "name": "Miami-Dade County Public Schools",
        "abbreviation": "M-DCPS",
        "ee_id_digits": 6
    },
    "springfield_high": {
        "name": "Springfield Unified School District",
        "abbreviation": "SUSD",
        "ee_id_digits": 7
    }
}

# ===========================================
# DataImpulse Proxy Configuration
# ===========================================
PROXY_ENABLED = os.getenv("PROXY_ENABLED", "false").lower() == "true"
PROXY_HOST = os.getenv("PROXY_HOST", "gw.dataimpulse.com")
PROXY_PORT = os.getenv("PROXY_PORT", "10000")  # 10000 for sticky session
PROXY_USER = os.getenv("PROXY_USER", "")
PROXY_PASS = os.getenv("PROXY_PASS", "")
PROXY_COUNTRY = os.getenv("PROXY_COUNTRY", "us")
PROXY_STATE = os.getenv("PROXY_STATE", "ny")
PROXY_SESSION = os.getenv("PROXY_SESSION", "default")


def get_proxy_url(session_id: str = None) -> str:
    """
    Build DataImpulse proxy URL.
    
    Uses simple username format for compatibility with port 823.
    """
    if not PROXY_ENABLED or not PROXY_USER:
        return None
    
    # Simple format: user:pass@host:port
    # Works with both port 823 and 10000
    return f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"


def get_proxy_dict(session_id: str = None) -> dict:
    """
    Get proxy config as dict for httpx.
    
    Returns:
        {"http://": url, "https://": url} or None if disabled
    """
    url = get_proxy_url(session_id)
    if not url:
        return None
    return {
        "http://": url,
        "https://": url
    }


