"""
Veterans Scraper - Under 70 years old
Scrape from NGL with birth year filter (1955+)
"""
import json
import random
import time
import re
import base64
import logging
import httpx
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Output file
OUTPUT_FILE = Path(__file__).parent / "data" / "young_ngl_veterans.json"

# API endpoints
SEARCH_URL = "https://gravelocator.cem.va.gov/ngl/result"

# Minimum birth year (1955 = under 70)
MIN_BIRTH_YEAR = 1955

# Common surnames
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
]

BRANCH_MAP = {
    "US ARMY": {"id": 4070, "name": "Army"},
    "US NAVY": {"id": 4072, "name": "Navy"},
    "US AIR FORCE": {"id": 4073, "name": "Air Force"},
    "US MARINE CORPS": {"id": 4071, "name": "Marine Corps"},
    "US COAST GUARD": {"id": 4074, "name": "Coast Guard"},
    "ARMY": {"id": 4070, "name": "Army"},
    "NAVY": {"id": 4072, "name": "Navy"},
    "AIR FORCE": {"id": 4073, "name": "Air Force"},
    "MARINE CORPS": {"id": 4071, "name": "Marine Corps"},
}


def format_date(date_str: str) -> str:
    """Format date from MM/DD/YYYY to YYYY/MM/DD."""
    if not date_str:
        return ""
    match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_str.strip())
    if match:
        month, day, year = match.groups()
        return f"{year}/{month.zfill(2)}/{day.zfill(2)}"
    return ""


def get_birth_year(date_str: str) -> int:
    """Get birth year from formatted date."""
    if not date_str:
        return 0
    try:
        return int(date_str.split("/")[0])
    except:
        return 0


def clean_name(raw_name: str) -> str:
    """Clean name string."""
    if not raw_name:
        return ""
    name = re.sub(r'^[\'\"\d~\-\s]+', '', raw_name)
    name = re.sub(r'[\'\"\d~\-\s]+$', '', name)
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'[^A-Za-z\'\-\s]', '', name)
    return name.strip().upper()


def search_veterans(last_name: str) -> str:
    """Search NGL."""
    form_data = {
        "lastName": last_name,
        "lastNameOpt": "1",
        "firstName": "",
        "firstNameOpt": "1",
        "middleName": "",
        "middleNameOpt": "1",
        "p_birthMM": "",
        "p_birthYY": "",
        "p_deathMM": "",
        "p_deathYY": "",
        "cemetery": "",
        "nglUP": "1",
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.post(SEARCH_URL, data=form_data, headers=headers)
            if response.status_code == 200:
                return response.text
    except Exception as e:
        logger.error(f"Request failed: {e}")
    return ""


def parse_results(html: str, min_year: int) -> List[Dict]:
    """Parse NGL HTML and filter by birth year."""
    veterans = []
    if not html:
        return veterans
    
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='searchResults')
    if not table:
        return veterans
    
    tbody = table.find('tbody')
    if not tbody:
        return veterans
    
    current = {}
    
    for row in tbody.find_all('tr'):
        if row.find('hr'):
            if current.get('name') and current.get('birth'):
                birth_year = get_birth_year(current['birth'])
                if birth_year >= min_year:
                    # Clean name
                    current['name'] = clean_name(current['name'])
                    if current['name']:
                        # Add branch info
                        branch = current.get('branch', 'US ARMY')
                        branch_info = BRANCH_MAP.get(branch, {"id": 4070, "name": "Army"})
                        current['branch_id'] = branch_info['id']
                        current['branch_name'] = branch_info['name']
                        
                        # Parse name
                        parts = current['name'].split()
                        if len(parts) >= 2:
                            current['lastname'] = parts[-1]
                            current['firstname'] = ' '.join(parts[:-1])
                        else:
                            current['lastname'] = current['name']
                            current['firstname'] = ''
                        
                        # Generate discharge date
                        days_ago = random.randint(30, 330)
                        discharge = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
                        current['discharge'] = discharge
                        current['url'] = ''
                        
                        veterans.append(current.copy())
            current = {}
            continue
        
        cells = row.find_all(['th', 'td'])
        for i, cell in enumerate(cells):
            if cell.name == 'th':
                header = cell.get_text(strip=True).lower()
                if i + 1 < len(cells):
                    value = cells[i + 1].get_text(strip=True)
                    
                    if 'name:' in header:
                        if ',' in value:
                            parts = value.split(',', 1)
                            last = parts[0].strip()
                            first = parts[1].strip() if len(parts) > 1 else ""
                            current['name'] = f"{first} {last}"
                        else:
                            current['name'] = value
                    elif 'date of birth' in header:
                        current['birth'] = format_date(value)
                    elif 'date of death' in header:
                        current['death'] = format_date(value)
                    elif 'rank' in header or 'branch' in header:
                        val_upper = value.upper()
                        for key in BRANCH_MAP:
                            if key in val_upper:
                                current['branch'] = key
                                break
                        if 'branch' not in current:
                            current['branch'] = 'US ARMY'
    
    # Last record
    if current.get('name') and current.get('birth'):
        birth_year = get_birth_year(current['birth'])
        if birth_year >= min_year:
            current['name'] = clean_name(current['name'])
            if current['name']:
                branch = current.get('branch', 'US ARMY')
                branch_info = BRANCH_MAP.get(branch, {"id": 4070, "name": "Army"})
                current['branch_id'] = branch_info['id']
                current['branch_name'] = branch_info['name']
                parts = current['name'].split()
                if len(parts) >= 2:
                    current['lastname'] = parts[-1]
                    current['firstname'] = ' '.join(parts[:-1])
                else:
                    current['lastname'] = current['name']
                    current['firstname'] = ''
                days_ago = random.randint(30, 330)
                current['discharge'] = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
                current['url'] = ''
                veterans.append(current.copy())
    
    return veterans


def scrape_all(max_per_name: int = 100, max_total: int = 3000) -> List[Dict]:
    """Scrape young veterans from NGL."""
    all_veterans = []
    seen = set()
    
    logger.info(f"Starting NGL scrape for veterans born >= {MIN_BIRTH_YEAR}")
    logger.info(f"Surnames: {len(COMMON_NAMES)}, Max total: {max_total}")
    
    for surname in COMMON_NAMES:
        if len(all_veterans) >= max_total:
            break
        
        logger.info(f"Searching: {surname}...")
        
        html = search_veterans(surname)
        if html:
            veterans = parse_results(html, MIN_BIRTH_YEAR)
            
            count = 0
            for v in veterans:
                if count >= max_per_name or len(all_veterans) >= max_total:
                    break
                if v['name'] in seen:
                    continue
                seen.add(v['name'])
                all_veterans.append(v)
                count += 1
            
            logger.info(f"  Found {count} young veterans")
        
        logger.info(f"  Total: {len(all_veterans)}")
        time.sleep(random.uniform(0.5, 1.5))
    
    return all_veterans


def main():
    print("=" * 60)
    print("  NGL YOUNG VETERANS SCRAPER")
    print(f"  Filter: Born >= {MIN_BIRTH_YEAR} (under 70)")
    print("=" * 60)
    
    veterans = scrape_all(max_per_name=50, max_total=2000)
    
    print(f"\nTotal scraped: {len(veterans)}")
    
    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted(veterans, key=lambda x: x['name']), f, indent=2, ensure_ascii=False)
    print(f"Saved to {OUTPUT_FILE}")
    
    # Sample
    print("\nSample:")
    for v in veterans[:5]:
        print(f"  {v['name']}: {v['birth']} - {v.get('death', 'alive?')}")


if __name__ == "__main__":
    main()
