"""
ANC Explorer Scraper v4 - Using EISS API with DOB/DOD
Complete veteran data with birth dates and death dates
"""
import json
import random
import time
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
OUTPUT_FILE = Path(__file__).parent / "data" / "anc_veterans.json"

# EISS API endpoint
EISS_BASE_URL = "https://ancexplorer.army.mil/proxy/proxy.ashx?https://wspublic.eiss.army.mil/v1/IssRetrieveServices.svc/search"

# Import proxy
try:
    from config.proxy_manager import get_proxy_url
except ImportError:
    def get_proxy_url(): return None

# Common last names to search (expanded list)
COMMON_NAMES = [
    # Top 30 from veterans_usa.json
    "SMITH", "JOHNSON", "WILLIAMS", "BROWN", "JONES",
    "GARCIA", "MILLER", "DAVIS", "RODRIGUEZ", "MARTINEZ",
    "HERNANDEZ", "LOPEZ", "GONZALEZ", "WILSON", "ANDERSON",
    "THOMAS", "TAYLOR", "MOORE", "JACKSON", "MARTIN",
    # Additional common surnames
    "LEE", "PEREZ", "THOMPSON", "WHITE", "HARRIS",
    "SANCHEZ", "CLARK", "RAMIREZ", "LEWIS", "ROBINSON",
    "WALKER", "YOUNG", "ALLEN", "KING", "WRIGHT",
    "SCOTT", "TORRES", "NGUYEN", "HILL", "FLORES",
    "GREEN", "ADAMS", "NELSON", "BAKER", "HALL",
    "RIVERA", "CAMPBELL", "MITCHELL", "CARTER", "ROBERTS",
    "GOMEZ", "PHILLIPS", "EVANS", "TURNER", "DIAZ",
    "PARKER", "CRUZ", "EDWARDS", "COLLINS", "REYES",
    "STEWART", "MORRIS", "MORALES", "MURPHY", "COOK",
    # More common names
    "ROGERS", "GUTIERREZ", "ORTIZ", "MORGAN", "COOPER",
    "PETERSON", "BAILEY", "REED", "KELLY", "HOWARD",
    "RAMOS", "KIM", "COX", "WARD", "RICHARDSON",
    "WATSON", "BROOKS", "CHAVEZ", "WOOD", "JAMES",
    "BENNETT", "GRAY", "MENDOZA", "RUIZ", "HUGHES",
]

# Branch mapping
BRANCH_MAP = {
    "USA": "US ARMY",
    "USN": "US NAVY",
    "USAF": "US AIR FORCE",
    "USMC": "US MARINE CORPS",
    "USCG": "US COAST GUARD",
    "USSF": "US SPACE FORCE",
    "": "US ARMY",  # Default
}


def parse_date(date_str: str) -> str:
    """Parse date from API format to YYYY/MM/DD."""
    if not date_str:
        return ""
    
    # Format: "02/15/1914 00:00"
    try:
        parts = date_str.split(" ")[0]  # Remove time
        month, day, year = parts.split("/")
        return f"{year}/{month.zfill(2)}/{day.zfill(2)}"
    except:
        return ""


def query_eiss(surname: str, start: int = 0, limit: int = 100) -> List[Dict]:
    """Query EISS API for veterans by surname."""
    # Build URL with proper encoding
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
    """Parse EISS record to standard format."""
    first = record.get("PRIMARYFIRSTNAME", "").strip()
    middle = record.get("PRIMARYMIDDLENAME", "").strip()
    last = record.get("PRIMARYLASTNAME", "").strip()
    
    # Combine name
    name_parts = [p for p in [first, middle, last] if p]
    name = " ".join(name_parts).upper()
    
    # Parse dates
    dob = parse_date(record.get("DOB", ""))
    dod = parse_date(record.get("DOD", ""))
    
    # Parse branch
    branch_code = record.get("BRANCHOFSERVICE", "").strip()
    branch = BRANCH_MAP.get(branch_code, "US ARMY")
    
    # Cemetery info
    cemetery = record.get("CemeteryName", "")
    section = record.get("SECTION", "")
    grave = record.get("GRAVE", "")
    
    return {
        "branch": branch,
        "name": name,
        "birth": dob,
        "death": dod,
        "url": "",  # EISS doesn't provide URLs
        "cemetery": cemetery,
        "section": section,
        "grave": grave
    }


def scrape_all(max_per_name: int = 50, max_total: int = 1000) -> List[Dict]:
    """Scrape veterans from EISS API."""
    all_veterans = []
    seen_names = set()
    
    logger.info(f"Starting EISS scrape with {len(COMMON_NAMES)} surnames...")
    logger.info(f"Using proxy: {get_proxy_url() is not None}")
    
    for surname in COMMON_NAMES:
        if len(all_veterans) >= max_total:
            logger.info(f"Reached max total: {max_total}")
            break
        
        logger.info(f"Querying: {surname}...")
        
        # Query with pagination
        start = 0
        name_count = 0
        
        while name_count < max_per_name:
            records = query_eiss(surname, start=start, limit=100)
            
            if not records:
                break
            
            for rec in records:
                if name_count >= max_per_name:
                    break
                if len(all_veterans) >= max_total:
                    break
                
                veteran = parse_veteran(rec)
                
                # Skip if no name or missing birth date
                if not veteran["name"]:
                    continue
                
                # Skip duplicates
                if veteran["name"] in seen_names:
                    continue
                
                # Only include records with birth date
                if not veteran["birth"]:
                    continue
                
                seen_names.add(veteran["name"])
                all_veterans.append(veteran)
                name_count += 1
            
            start += 100
            
            # Rate limiting
            time.sleep(0.5)
            
            # If we got less than 100, no more results
            if len(records) < 100:
                break
        
        logger.info(f"  Found {name_count} veterans for '{surname}'")
        logger.info(f"  Total so far: {len(all_veterans)}")
    
    return all_veterans


def save_veterans(veterans: List[Dict]):
    """Save veterans to JSON file."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Sort by name
    veterans_sorted = sorted(veterans, key=lambda x: x.get("name", ""))
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(veterans_sorted, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(veterans_sorted)} veterans to {OUTPUT_FILE}")


def main():
    """Main scraper function."""
    print("=" * 60)
    print("ANC EXPLORER SCRAPER v4 (EISS API with DOB/DOD)")
    print("=" * 60)
    print()
    
    # Check proxy
    proxy = get_proxy_url()
    if proxy:
        print(f"Proxy: {proxy[:50]}...")
    else:
        print("Proxy: None (direct connection)")
    print()
    
    # Scrape
    veterans = scrape_all(max_per_name=80, max_total=5000)
    
    print()
    print(f"Total veterans scraped: {len(veterans)}")
    
    # Save
    save_veterans(veterans)
    
    # Show sample
    print()
    print("Sample veterans:")
    for v in veterans[:5]:
        print(f"  - {v['name']}")
        print(f"    Birth: {v['birth']}, Death: {v['death']}, Branch: {v['branch']}")


if __name__ == "__main__":
    main()
