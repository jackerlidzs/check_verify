"""Veteran Profile Generator"""
import json
import random
import logging
from pathlib import Path
from typing import Dict, Optional

from . import config

logger = logging.getLogger(__name__)

# Cache for loaded profiles
_profiles_cache: list = []

# Track used veterans to avoid repeat
_used_veterans: set = set()
USED_VETERANS_FILE = Path(__file__).parent / "data" / "used_veterans.json"


def load_used_veterans() -> set:
    """Load set of used veteran identifiers (name+birth)."""
    global _used_veterans
    if USED_VETERANS_FILE.exists():
        try:
            _used_veterans = set(json.loads(USED_VETERANS_FILE.read_text()))
        except Exception:
            _used_veterans = set()
    return _used_veterans


def mark_veteran_used(name: str, birth: str):
    """Mark a veteran profile as used."""
    key = f"{name.lower()}|{birth}"
    _used_veterans.add(key)
    try:
        USED_VETERANS_FILE.write_text(json.dumps(list(_used_veterans)))
    except Exception as e:
        logger.warning(f"Failed to save used veterans: {e}")


def reset_used_veterans():
    """Reset all used veterans."""
    global _used_veterans
    _used_veterans = set()
    if USED_VETERANS_FILE.exists():
        USED_VETERANS_FILE.unlink()


def _load_profiles() -> list:
    """Load veteran profiles from JSONL file"""
    global _profiles_cache
    
    if _profiles_cache:
        return _profiles_cache
    
    data_file = Path(__file__).parent / config.DATA_FILE
    
    if not data_file.exists():
        logger.error(f"Data file not found: {data_file}")
        return []
    
    profiles = []
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        profile = json.loads(line)
                        # Only include profiles with valid data
                        if profile.get('name') and profile.get('birth'):
                            # Filter out veterans too old (born before 1940)
                            birth = profile.get('birth', '')
                            birth_year = birth.split('/')[0] if '/' in birth else birth[:4]
                            if birth_year.isdigit() and int(birth_year) >= 1940:
                                profiles.append(profile)
                    except json.JSONDecodeError:
                        continue
        
        _profiles_cache = profiles
        logger.info(f"Loaded {len(profiles)} veteran profiles (age-filtered)")
        return profiles
    
    except Exception as e:
        logger.error(f"Failed to load profiles: {e}")
        return []


def get_random_profile() -> Optional[Dict]:
    """Get a random unused veteran profile from the database"""
    profiles = _load_profiles()
    
    if not profiles:
        return None
    
    # Load used veterans
    load_used_veterans()
    
    # Filter out used profiles
    unused = [
        p for p in profiles
        if f"{p.get('name', '').lower()}|{p.get('birth', '')}" not in _used_veterans
    ]
    
    if not unused:
        # All used - reset and use all
        logger.info("All veterans used, resetting...")
        reset_used_veterans()
        unused = profiles
    
    return random.choice(unused)


def parse_name(full_name: str) -> Dict[str, str]:
    """Parse full name into first and last name"""
    parts = full_name.strip().split()
    
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = ' '.join(parts[1:])
    elif len(parts) == 1:
        first_name = parts[0]
        last_name = "Smith"  # Default last name
    else:
        first_name = "John"
        last_name = "Doe"
    
    return {
        "first_name": first_name,
        "last_name": last_name
    }


def parse_birth_date(birth_str: str) -> str:
    """Convert birth date from YYYY/MM/DD to YYYY-MM-DD format"""
    if not birth_str:
        return "1970-01-01"
    
    # Replace / with -
    return birth_str.replace('/', '-')


def generate_discharge_date() -> str:
    """Generate discharge date in 2025 with random month (1-11) and day"""
    month = random.randint(1, 11)
    
    # Days per month (simplified, no leap year consideration needed)
    days_in_month = {
        1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
        7: 31, 8: 31, 9: 30, 10: 31, 11: 30
    }
    
    day = random.randint(1, days_in_month[month])
    
    return f"2025-{month:02d}-{day:02d}"


def get_organization(branch: str) -> Dict:
    """Get SheerID organization info from branch name"""
    if not branch:
        return config.DEFAULT_ORGANIZATION
    
    # Normalize branch name
    branch_upper = branch.upper().strip()
    
    # Direct match
    if branch_upper in config.ORGANIZATIONS:
        return config.ORGANIZATIONS[branch_upper]
    
    # Partial match
    for key, org in config.ORGANIZATIONS.items():
        if key in branch_upper or branch_upper in key:
            return org
    
    # Default
    return config.DEFAULT_ORGANIZATION


def generate_veteran_info() -> Optional[Dict]:
    """Generate complete veteran info for verification"""
    profile = get_random_profile()
    
    if not profile:
        logger.error("No profiles available")
        return None
    
    name = parse_name(profile.get('name', ''))
    birth_date = parse_birth_date(profile.get('birth', ''))
    discharge_date = generate_discharge_date()
    organization = get_organization(profile.get('branch', ''))
    
    return {
        "first_name": name["first_name"],
        "last_name": name["last_name"],
        "birth_date": birth_date,
        "discharge_date": discharge_date,
        "organization": organization,
        "branch": profile.get('branch', 'Unknown'),
        # Include original profile for debugging
        "_original_profile": profile
    }


def generate_email(first_name: str, last_name: str) -> str:
    """Generate a random email address"""
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
    random_num = random.randint(100, 999)
    domain = random.choice(domains)
    
    # Remove spaces and special characters from names
    first = first_name.lower().replace(' ', '').replace('-', '')
    last = last_name.lower().replace(' ', '').replace('-', '')
    
    return f"{first}.{last}{random_num}@{domain}"

