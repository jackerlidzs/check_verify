"""
K12 Staff Directory URL Finder
Searches for staff directory URLs for schools in k12_schools.json

Usage:
    python find_staff_urls.py --batch 1  # Process schools 1-20
    python find_staff_urls.py --batch 2  # Process schools 21-40
"""

import json
import httpx
import re
import time
from pathlib import Path
from typing import Optional, Dict, List
import argparse

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
SCHOOLS_FILE = DATA_DIR / "k12_schools.json"
OUTPUT_FILE = Path(__file__).parent / "found_staff_urls.json"

BATCH_SIZE = 20

# Common staff directory URL patterns
STAFF_URL_PATTERNS = [
    "/staff",
    "/faculty",
    "/staff-directory",
    "/faculty-staff",
    "/faculty-and-staff",
    "/about/faculty",
    "/about/staff",
    "/our-team",
    "/team",
    "/people",
]


def load_schools() -> List[Dict]:
    """Load K12 schools from JSON file."""
    with open(SCHOOLS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_found_urls() -> Dict[str, str]:
    """Load previously found URLs."""
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_found_urls(urls: Dict[str, str]):
    """Save found URLs to JSON file."""
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(urls, f, indent=2, ensure_ascii=False)


def generate_possible_domains(school_name: str, city: str, state: str) -> List[str]:
    """Generate possible domain names for a school."""
    # Clean school name
    name_lower = school_name.lower()
    name_clean = re.sub(r'[^a-z0-9\s]', '', name_lower)
    words = name_clean.split()
    
    # Common domain patterns
    domains = []
    
    # Pattern 1: schoolname.org
    if len(words) > 0:
        domains.append(f"{''.join(words)}.org")
        domains.append(f"{'-'.join(words)}.org")
    
    # Pattern 2: abbreviation if long name (e.g., "Academy For Academic Excellence" -> "afae.org")
    if len(words) >= 3:
        abbrev = ''.join(word[0] for word in words if word not in ['the', 'of', 'for', 'and', 'at'])
        if len(abbrev) >= 3:
            domains.append(f"{abbrev}.org")
    
    # Pattern 3: Public school patterns (k12)
    state_lower = state.lower()
    city_words = re.sub(r'[^a-z0-9\s]', '', city.lower()).split()
    if city_words:
        city_clean = ''.join(city_words)
        domains.append(f"{city_clean}.k12.{state_lower}.us")
    
    return domains


def check_url_exists(url: str, client: httpx.Client) -> bool:
    """Check if a URL exists (returns 200)."""
    try:
        response = client.head(url, timeout=5.0, follow_redirects=True)
        return response.status_code == 200
    except:
        return False


def find_staff_url(school: Dict, client: httpx.Client) -> Optional[str]:
    """Try to find staff directory URL for a school."""
    domains = generate_possible_domains(
        school['name'], 
        school.get('city', ''), 
        school.get('state', '')
    )
    
    for domain in domains[:3]:  # Limit to first 3 domain guesses
        base_url = f"https://www.{domain}"
        
        # Try each staff URL pattern
        for pattern in STAFF_URL_PATTERNS[:5]:  # Limit patterns
            full_url = f"{base_url}{pattern}"
            if check_url_exists(full_url, client):
                return full_url
        
        time.sleep(0.5)  # Rate limiting
    
    return None


def search_google_for_staff_url(school_name: str, city: str, state: str) -> Optional[str]:
    """
    Search Google for staff directory (requires manual verification).
    Returns search query instead of URL.
    """
    query = f"{school_name} {city} {state} staff directory faculty"
    return f"https://www.google.com/search?q={query.replace(' ', '+')}"


def process_batch(batch_number: int):
    """Process a batch of schools."""
    schools = load_schools()
    found_urls = load_found_urls()
    
    start_idx = (batch_number - 1) * BATCH_SIZE
    end_idx = start_idx + BATCH_SIZE
    
    batch_schools = schools[start_idx:end_idx]
    
    if not batch_schools:
        print(f"No schools found for batch {batch_number}")
        return
    
    print(f"\n=== BATCH {batch_number}: Schools {start_idx+1}-{end_idx} ===\n")
    
    with httpx.Client(
        headers={'User-Agent': 'Mozilla/5.0'},
        follow_redirects=True
    ) as client:
        for i, school in enumerate(batch_schools):
            school_id = str(school['id'])
            school_name = school['name']
            
            # Skip if already found
            if school_id in found_urls:
                print(f"[{i+1}/{len(batch_schools)}] SKIP: {school_name} (already found)")
                continue
            
            print(f"[{i+1}/{len(batch_schools)}] Searching: {school_name}...", end=" ")
            
            url = find_staff_url(school, client)
            
            if url:
                found_urls[school_id] = url
                print(f"FOUND: {url}")
            else:
                print("NOT FOUND")
            
            time.sleep(1)  # Rate limiting
    
    save_found_urls(found_urls)
    print(f"\nTotal URLs found: {len(found_urls)}")
    print(f"Saved to: {OUTPUT_FILE}")


def list_found():
    """List all found URLs."""
    found_urls = load_found_urls()
    schools = load_schools()
    
    # Create ID -> name mapping
    id_to_name = {str(s['id']): s['name'] for s in schools}
    
    print(f"\n=== FOUND STAFF URLS ({len(found_urls)}) ===\n")
    for school_id, url in found_urls.items():
        name = id_to_name.get(school_id, "Unknown")
        print(f"[{school_id}] {name}")
        print(f"    {url}")


def export_to_scraper():
    """Export found URLs to scraper config format."""
    found_urls = load_found_urls()
    
    print("\n# Copy this to teacher_scraper.py SCHOOL_STAFF_URLS:\n")
    print("SCHOOL_STAFF_URLS = {")
    for school_id, url in found_urls.items():
        print(f'    "{school_id}": "{url}",')
    print("}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="K12 Staff Directory URL Finder")
    parser.add_argument("--batch", type=int, help="Batch number to process (1, 2, 3...)")
    parser.add_argument("--list", action="store_true", help="List found URLs")
    parser.add_argument("--export", action="store_true", help="Export to scraper format")
    
    args = parser.parse_args()
    
    if args.list:
        list_found()
    elif args.export:
        export_to_scraper()
    elif args.batch:
        process_batch(args.batch)
    else:
        print("Usage:")
        print("  python find_staff_urls.py --batch 1  # Process schools 1-20")
        print("  python find_staff_urls.py --list     # List found URLs")
        print("  python find_staff_urls.py --export   # Export to scraper format")
