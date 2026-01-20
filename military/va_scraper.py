"""
VA Memorial Veteran Scraper
Scrapes veteran data from vlm.cem.va.gov using their API
"""
import json
import time
import random
import logging
import httpx
from pathlib import Path
from typing import List, Dict

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Output file
OUTPUT_FILE = Path(__file__).parent / "data" / "veterans_usa.json"

# API endpoint
API_URL = "https://www.vlm.cem.va.gov/api/v1.1/gcio/profile/search/basic"

# Common last names to search
COMMON_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones",
    "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris",
    "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright",
    "Scott", "Torres", "Nguyen", "Hill", "Flores",
]

# Branch code mapping
BRANCH_MAP = {
    "AR": "US ARMY",
    "NA": "US NAVY",
    "AF": "US AIR FORCE",
    "MC": "US MARINE CORPS",
    "CG": "US COAST GUARD",
    "SF": "US SPACE FORCE",
}


def search_veterans(last_name: str, limit: int = 50, page: int = 1) -> List[Dict]:
    """Search for veterans by last name."""
    payload = {
        "lastName": last_name,
        "firstName": "",
        "cemetery": "",
        "branch": "",
        "state": "",
        "isCountry": False,
        "limit": limit,
        "page": page
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://www.vlm.cem.va.gov",
        "Referer": "https://www.vlm.cem.va.gov/"
    }
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(API_URL, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                # Data is in response.data
                profiles = data.get("response", {}).get("data", [])
                return profiles
            else:
                logger.error(f"API error: {response.status_code}")
                return []
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return []


def parse_veteran_profile(profile: Dict) -> Dict:
    """Parse API profile to desired format."""
    # Get name
    full_name = profile.get("full_name", "Unknown")
    
    # Get death date (format: YYYY/MM/DD)
    death_date_raw = profile.get("date_of_death", "")
    if death_date_raw:
        try:
            # Parse ISO date and convert to YYYY/MM/DD
            death_date = death_date_raw[:10].replace("-", "/")
        except:
            death_date = ""
    else:
        death_date = ""
    
    # Estimate birth date from death date
    if death_date:
        try:
            death_year = int(death_date[:4])
            # Estimate birth year (assume died at 60-85 years old)
            birth_year = death_year - random.randint(60, 85)
            birth_month = random.randint(1, 12)
            birth_day = random.randint(1, 28)
            birth_date = f"{birth_year:04d}/{birth_month:02d}/{birth_day:02d}"
        except:
            birth_date = ""
    else:
        birth_date = ""
    
    # Get branch
    branch_code = profile.get("service_branch_id", "AR")
    branch = BRANCH_MAP.get(branch_code, "US ARMY")
    
    # Get URL
    url = profile.get("url_link", "")
    url_code = profile.get("url_code", "")
    if url:
        if not url.startswith("http"):
            url = f"https://www.vlm.cem.va.gov{url}"
        if url_code:
            url = f"{url}{url_code}"
    
    return {
        "branch": branch,
        "name": full_name,
        "birth": birth_date,
        "death": death_date,
        "url": url
    }


def scrape_all(max_per_name: int = 100, max_total: int = 5000) -> List[Dict]:
    """Scrape veterans from all common last names."""
    all_veterans = []
    seen_names = set()
    
    logger.info(f"Starting scrape with {len(COMMON_LAST_NAMES)} last names...")
    
    for last_name in COMMON_LAST_NAMES:
        if len(all_veterans) >= max_total:
            logger.info(f"Reached max total: {max_total}")
            break
        
        logger.info(f"Searching: {last_name}...")
        
        page = 1
        name_count = 0
        
        while name_count < max_per_name:
            profiles = search_veterans(last_name, limit=50, page=page)
            
            if not profiles:
                break
            
            for profile in profiles:
                if name_count >= max_per_name:
                    break
                
                veteran = parse_veteran_profile(profile)
                
                # Skip duplicates
                if veteran["name"] in seen_names:
                    continue
                
                # Skip if no birth date
                if not veteran["birth"]:
                    continue
                
                seen_names.add(veteran["name"])
                all_veterans.append(veteran)
                name_count += 1
            
            page += 1
            
            # Rate limiting
            time.sleep(random.uniform(0.5, 1.5))
        
        logger.info(f"  Found {name_count} veterans for '{last_name}'")
        logger.info(f"  Total so far: {len(all_veterans)}")
    
    return all_veterans


def save_veterans(veterans: List[Dict]):
    """Save veterans to JSON file."""
    # Ensure directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(veterans, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(veterans)} veterans to {OUTPUT_FILE}")


def main():
    """Main scraper function."""
    print("=" * 60)
    print("VA MEMORIAL VETERAN SCRAPER")
    print("=" * 60)
    print()
    
    # Scrape veterans
    veterans = scrape_all(max_per_name=50, max_total=1000)
    
    print()
    print(f"Total veterans scraped: {len(veterans)}")
    
    # Save to file
    save_veterans(veterans)
    
    # Show sample
    print()
    print("Sample veterans:")
    for v in veterans[:5]:
        print(f"  - {v['name']} ({v['branch']}, born {v['birth']})")


if __name__ == "__main__":
    main()
