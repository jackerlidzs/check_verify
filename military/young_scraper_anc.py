"""
Young Veterans Scraper - ANC Explorer
Scrape veterans born after 1985 (under 40 years old)
Phase 1: ANC
"""
import json
import random
import time
import logging
import httpx
from pathlib import Path
from typing import List, Dict
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Output file
OUTPUT_FILE = Path(__file__).parent / "data" / "young_anc_veterans.json"

# EISS API endpoint
EISS_BASE_URL = "https://ancexplorer.army.mil/proxy/proxy.ashx?https://wspublic.eiss.army.mil/v1/IssRetrieveServices.svc/search"

# Minimum birth year (1985 = under 40)
MIN_BIRTH_YEAR = 1985

# Import proxy
try:
    from config.proxy_manager import get_proxy_url
except ImportError:
    def get_proxy_url(): return None

# Common last names
COMMON_NAMES = [
    "SMITH", "JOHNSON", "WILLIAMS", "BROWN", "JONES",
    "GARCIA", "MILLER", "DAVIS", "RODRIGUEZ", "MARTINEZ",
    "HERNANDEZ", "LOPEZ", "GONZALEZ", "WILSON", "ANDERSON",
    "THOMAS", "TAYLOR", "MOORE", "JACKSON", "MARTIN",
    "LEE", "PEREZ", "THOMPSON", "WHITE", "HARRIS",
    "SANCHEZ", "CLARK", "RAMIREZ", "LEWIS", "ROBINSON",
    "WALKER", "YOUNG", "ALLEN", "KING", "WRIGHT",
    "SCOTT", "TORRES", "NGUYEN", "HILL", "FLORES",
    "GREEN", "ADAMS", "NELSON", "BAKER", "HALL",
    "RIVERA", "CAMPBELL", "MITCHELL", "CARTER", "ROBERTS",
    "GOMEZ", "PHILLIPS", "EVANS", "TURNER", "DIAZ",
    "PARKER", "CRUZ", "EDWARDS", "COLLINS", "REYES",
    "STEWART", "MORRIS", "MORALES", "MURPHY", "COOK",
    "ROGERS", "GUTIERREZ", "ORTIZ", "MORGAN", "COOPER",
    "PETERSON", "BAILEY", "REED", "KELLY", "HOWARD",
    "RAMOS", "KIM", "COX", "WARD", "RICHARDSON",
]

BRANCH_MAP = {
    "USA": "US ARMY",
    "USN": "US NAVY",
    "USAF": "US AIR FORCE",
    "USMC": "US MARINE CORPS",
    "USCG": "US COAST GUARD",
    "USSF": "US SPACE FORCE",
    "": "US ARMY",
}

BRANCH_ORG_MAP = {
    "US ARMY": {"id": 4070, "name": "Army"},
    "US NAVY": {"id": 4072, "name": "Navy"},
    "US AIR FORCE": {"id": 4073, "name": "Air Force"},
    "US MARINE CORPS": {"id": 4071, "name": "Marine Corps"},
    "US COAST GUARD": {"id": 4074, "name": "Coast Guard"},
}


def parse_date(date_str: str) -> str:
    """Parse date from API format to YYYY/MM/DD."""
    if not date_str:
        return ""
    try:
        parts = date_str.split(" ")[0]
        month, day, year = parts.split("/")
        return f"{year}/{month.zfill(2)}/{day.zfill(2)}"
    except:
        return ""


def get_birth_year(date_str: str) -> int:
    """Extract birth year from date string."""
    if not date_str:
        return 0
    try:
        parsed = parse_date(date_str)
        if parsed:
            return int(parsed.split("/")[0])
        parts = date_str.split(" ")[0]
        month, day, year = parts.split("/")
        return int(year)
    except:
        return 0


def query_eiss(surname: str, start: int = 0, limit: int = 100) -> List[Dict]:
    """Query EISS API for veterans by surname."""
    query = f"primarylastname~{surname}%2Ccemeteryid%3DALL"
    sort = "PrimaryLastName%2CPrimaryFirstName%2CPrimaryMiddleName%2CDOB%2CDOD"
    url = f"{EISS_BASE_URL}?AppId=Roi&q={query}&start={start}&limit={limit}&sortColumn={sort}&sortOrder=asc&f=json"
    
    try:
        proxy = get_proxy_url()
        with httpx.Client(proxy=proxy, timeout=30) as client:
            response = client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                records = data.get("SearchResult", {}).get("Records", [])
                return records
            else:
                logger.error(f"HTTP error: {response.status_code}")
                return []
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return []


def parse_veteran(record: Dict) -> Dict:
    """Parse veteran record from EISS."""
    first = record.get("PrimaryFirstName", "").strip().upper()
    middle = record.get("PrimaryMiddleName", "").strip().upper()
    last = record.get("PrimaryLastName", "").strip().upper()
    
    # Build full first name
    if middle:
        firstname = f"{first} {middle}"
    else:
        firstname = first
    
    # Parse dates
    dob = parse_date(record.get("DOB", ""))
    dod = parse_date(record.get("DOD", ""))
    
    # Parse branch
    branch_code = record.get("BRANCHOFSERVICE", "").strip()
    branch = BRANCH_MAP.get(branch_code, "US ARMY")
    branch_info = BRANCH_ORG_MAP.get(branch, {"id": 4070, "name": "Army"})
    
    # Generate discharge date (within 12 months)
    today = datetime.now()
    days_ago = random.randint(30, 330)
    discharge = (today - __import__('datetime').timedelta(days=days_ago)).strftime("%Y-%m-%d")
    
    return {
        "name": f"{firstname} {last}".strip(),
        "firstname": firstname,
        "lastname": last,
        "branch": branch,
        "branch_id": branch_info["id"],
        "branch_name": branch_info["name"],
        "birth": dob,
        "death": dod,
        "discharge": discharge,
        "url": "",
    }


def scrape_young_veterans(max_per_name: int = 200, max_total: int = 5000) -> List[Dict]:
    """Scrape young veterans (born after 1985)."""
    all_veterans = []
    seen_names = set()
    
    logger.info(f"Starting YOUNG veterans scrape (born >= {MIN_BIRTH_YEAR})")
    logger.info(f"Surnames: {len(COMMON_NAMES)}, Max/name: {max_per_name}, Max total: {max_total}")
    
    for surname in COMMON_NAMES:
        if len(all_veterans) >= max_total:
            logger.info(f"Reached max total: {max_total}")
            break
        
        logger.info(f"Querying: {surname}...")
        
        start = 0
        name_count = 0
        pages = 0
        
        while name_count < max_per_name and pages < 20:
            records = query_eiss(surname, start=start, limit=100)
            
            if not records:
                break
            
            young_count = 0
            for record in records:
                if name_count >= max_per_name or len(all_veterans) >= max_total:
                    break
                
                # Check birth year
                birth_year = get_birth_year(record.get("DOB", ""))
                if birth_year < MIN_BIRTH_YEAR:
                    continue
                
                veteran = parse_veteran(record)
                
                # Skip if no name or no DOB
                if not veteran["firstname"] or not veteran["birth"]:
                    continue
                
                # Skip duplicates
                if veteran["name"] in seen_names:
                    continue
                
                seen_names.add(veteran["name"])
                all_veterans.append(veteran)
                name_count += 1
                young_count += 1
            
            logger.info(f"  Page {pages+1}: found {young_count} young veterans")
            
            start += 100
            pages += 1
            time.sleep(0.5)
        
        logger.info(f"  Total for '{surname}': {name_count} young veterans")
        logger.info(f"  Grand total: {len(all_veterans)}")
        
        time.sleep(random.uniform(0.5, 1.0))
    
    return all_veterans


def save_veterans(veterans: List[Dict]):
    """Save veterans to JSON file."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    veterans_sorted = sorted(veterans, key=lambda x: x.get("name", ""))
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(veterans_sorted, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(veterans_sorted)} young veterans to {OUTPUT_FILE}")


def main():
    print("=" * 60)
    print("  YOUNG VETERANS SCRAPER - ANC (Phase 1)")
    print(f"  Filter: Born >= {MIN_BIRTH_YEAR} (under 40 years old)")
    print("=" * 60)
    print()
    
    veterans = scrape_young_veterans(max_per_name=200, max_total=5000)
    
    print()
    print(f"Total young veterans scraped: {len(veterans)}")
    
    save_veterans(veterans)
    
    print()
    print("Sample:")
    for v in veterans[:5]:
        print(f"  - {v['name']}")
        print(f"    Birth: {v['birth']}, Branch: {v['branch_name']}")


if __name__ == "__main__":
    main()
