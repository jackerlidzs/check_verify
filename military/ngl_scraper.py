"""
VA Grave Locator Scraper (NGL) v3
With pagination, expanded names from ANC/VLM, and name cleanup
"""
import json
import random
import time
import re
import base64
import logging
import httpx
from pathlib import Path
from typing import List, Dict, Set
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Files
OUTPUT_FILE = Path(__file__).parent / "data" / "ngl_veterans.json"
ANC_FILE = Path(__file__).parent / "data" / "anc_veterans.json"
VLM_FILE = Path(__file__).parent / "data" / "veterans_usa.json"

# API endpoints
SEARCH_URL = "https://gravelocator.cem.va.gov/ngl/result"
PAGE_URL = "https://gravelocator.cem.va.gov/ngl/result/{hash}/{params}"

# Branch mapping
BRANCH_MAP = {
    "US ARMY": "US ARMY",
    "US NAVY": "US NAVY",
    "US AIR FORCE": "US AIR FORCE",
    "US MARINE CORPS": "US MARINE CORPS",
    "US COAST GUARD": "US COAST GUARD",
    "ARMY": "US ARMY",
    "NAVY": "US NAVY",
    "AIR FORCE": "US AIR FORCE",
    "MARINE CORPS": "US MARINE CORPS",
}


def get_common_surnames() -> List[str]:
    """Get common surnames from ANC and VLM data."""
    surnames = set()
    
    # Base common names
    base_names = [
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
    ]
    surnames.update(base_names)
    
    # Add from ANC data
    if ANC_FILE.exists():
        try:
            with open(ANC_FILE, 'r', encoding='utf-8') as f:
                anc_data = json.load(f)
            for v in anc_data:
                name = v.get('name', '')
                if name:
                    parts = name.strip().split()
                    if parts:
                        # Last word is usually last name
                        surname = parts[-1].upper()
                        if len(surname) > 2 and surname.isalpha():
                            surnames.add(surname)
        except:
            pass
    
    # Add from VLM data
    if VLM_FILE.exists():
        try:
            with open(VLM_FILE, 'r', encoding='utf-8') as f:
                vlm_data = json.load(f)
            for v in vlm_data:
                name = v.get('name', '')
                if name:
                    parts = name.strip().split()
                    if parts:
                        surname = parts[-1].upper()
                        if len(surname) > 2 and surname.isalpha():
                            surnames.add(surname)
        except:
            pass
    
    logger.info(f"Collected {len(surnames)} unique surnames from all sources")
    return sorted(list(surnames))


def clean_name(raw_name: str) -> str:
    """Clean and validate name string."""
    if not raw_name:
        return ""
    
    # Remove special characters at start
    name = re.sub(r'^[\'\"\d~\-\s]+', '', raw_name)
    
    # Remove trailing special chars
    name = re.sub(r'[\'\"\d~\-\s]+$', '', name)
    
    # Replace multiple spaces with single space
    name = re.sub(r'\s+', ' ', name)
    
    # Remove any remaining non-letter non-space chars (except hyphen and apostrophe in middle)
    name = re.sub(r'[^A-Za-z\'\-\s]', '', name)
    
    # Clean up again
    name = re.sub(r'\s+', ' ', name).strip().upper()
    
    return name


def format_date(date_str: str) -> str:
    """Format date from MM/DD/YYYY to YYYY/MM/DD."""
    if not date_str:
        return ""
    
    match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_str.strip())
    if match:
        month, day, year = match.groups()
        return f"{year}/{month.zfill(2)}/{day.zfill(2)}"
    
    return ""


def search_veterans(last_name: str) -> tuple:
    """Perform initial search and return (HTML, session_hash)."""
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
        "Origin": "https://gravelocator.cem.va.gov",
        "Referer": "https://gravelocator.cem.va.gov/ngl/search"
    }
    
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.post(SEARCH_URL, data=form_data, headers=headers)
            
            if response.status_code == 200:
                html = response.text
                
                # Extract session hash from localStorage script
                # sessionVeteranDetails = JSON.stringify({"nl":"U01JVEg=",...})
                match = re.search(r'sessionVeteranDetails\s*=\s*JSON\.stringify\((\{[^}]+\})\)', html)
                if match:
                    params_json = match.group(1)
                    return html, params_json
                
                return html, None
            else:
                return "", None
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return "", None


def get_page(session_hash: str, params_json: str, page_num: int) -> str:
    """Get a specific page of results."""
    try:
        # Parse and update page number
        params = json.loads(params_json)
        
        # Encode page number to base64
        page_b64 = base64.b64encode(str(page_num).encode()).decode()
        params['pn'] = page_b64
        
        # Build URL
        new_params = json.dumps(params)
        url = f"https://gravelocator.cem.va.gov/ngl/result/{session_hash}/{new_params}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://gravelocator.cem.va.gov/ngl/result"
        }
        
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.text
    except Exception as e:
        logger.error(f"Page request failed: {e}")
    
    return ""


def parse_results(html: str) -> List[Dict]:
    """Parse search results from HTML."""
    veterans = []
    
    if not html:
        return veterans
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Get total count
    results_info = soup.find('p', id='results-content')
    total_count = 0
    if results_info:
        match = re.search(r'of\s+(\d+)', results_info.get_text())
        if match:
            total_count = int(match.group(1))
    
    # Find the results table
    table = soup.find('table', id='searchResults')
    if not table:
        return veterans
    
    tbody = table.find('tbody')
    if not tbody:
        return veterans
    
    current_veteran = {}
    
    for row in tbody.find_all('tr'):
        # Check for divider row
        if row.find('hr'):
            if current_veteran.get('name') and current_veteran.get('birth'):
                # Clean the name
                current_veteran['name'] = clean_name(current_veteran['name'])
                if current_veteran['name']:  # Only add if name is valid after cleaning
                    veterans.append(current_veteran.copy())
            current_veteran = {}
            continue
        
        cells = row.find_all(['th', 'td'])
        
        for i, cell in enumerate(cells):
            if cell.name == 'th':
                header_lower = cell.get_text(strip=True).lower()
                
                if i + 1 < len(cells):
                    value_cell = cells[i + 1]
                    value = value_cell.get_text(strip=True)
                    
                    if 'name:' in header_lower:
                        # Parse name: "LARRY, BARBARA ANN" -> "BARBARA ANN LARRY"
                        if ',' in value:
                            parts = value.split(',', 1)
                            last = parts[0].strip()
                            first = parts[1].strip() if len(parts) > 1 else ""
                            current_veteran['name'] = f"{first} {last}"
                        else:
                            current_veteran['name'] = value
                    
                    elif 'date of birth' in header_lower:
                        current_veteran['birth'] = format_date(value)
                    
                    elif 'date of death' in header_lower:
                        current_veteran['death'] = format_date(value)
                    
                    elif 'rank' in header_lower or 'branch' in header_lower:
                        branch = "US ARMY"
                        value_upper = value.upper()
                        for key, mapped in BRANCH_MAP.items():
                            if key in value_upper:
                                branch = mapped
                                break
                        current_veteran['branch'] = branch
                    
                    elif 'cemetery:' in header_lower:
                        cemetery_link = value_cell.find('a')
                        if cemetery_link:
                            current_veteran['cemetery'] = cemetery_link.get_text(strip=True)
                        else:
                            current_veteran['cemetery'] = value
    
    # Last veteran
    if current_veteran.get('name') and current_veteran.get('birth'):
        current_veteran['name'] = clean_name(current_veteran['name'])
        if current_veteran['name']:
            veterans.append(current_veteran.copy())
    
    return veterans


def scrape_all(max_per_name: int = 100, max_total: int = 2000, max_pages: int = 10) -> List[Dict]:
    """Scrape veterans from NGL with pagination."""
    surnames = get_common_surnames()
    all_veterans = []
    seen_names = set()
    
    logger.info(f"Starting NGL scrape with {len(surnames)} surnames...")
    logger.info(f"Target: {max_total} veterans, max {max_per_name}/name, {max_pages} pages/name")
    
    for surname in surnames:
        if len(all_veterans) >= max_total:
            logger.info(f"Reached max total: {max_total}")
            break
        
        logger.info(f"Searching: {surname}...")
        
        # Initial search
        html, params_json = search_veterans(surname)
        
        if not html:
            logger.warning(f"  No results for '{surname}'")
            continue
        
        # Get session hash from URL or scripts
        session_hash = None
        match = re.search(r'var\s+sessionHash\s*=\s*["\']([^"\']+)["\']', html)
        if match:
            session_hash = match.group(1)
        else:
            # Use a default hash pattern
            session_hash = "WnZOfk5LLywivlA0DgJMnQ=="
        
        # Parse first page
        veterans_page = parse_results(html)
        name_count = 0
        
        for v in veterans_page:
            if name_count >= max_per_name or len(all_veterans) >= max_total:
                break
            
            if v['name'] in seen_names:
                continue
            
            v.setdefault('branch', 'US ARMY')
            v.setdefault('death', '')
            v.setdefault('url', '')
            v.setdefault('cemetery', '')
            
            seen_names.add(v['name'])
            all_veterans.append(v)
            name_count += 1
        
        # Try pagination if we need more
        if params_json and name_count < max_per_name:
            for page in range(2, max_pages + 1):
                if name_count >= max_per_name or len(all_veterans) >= max_total:
                    break
                
                page_html = get_page(session_hash, params_json, page)
                if not page_html:
                    break
                
                veterans_page = parse_results(page_html)
                if not veterans_page:
                    break
                
                for v in veterans_page:
                    if name_count >= max_per_name or len(all_veterans) >= max_total:
                        break
                    
                    if v['name'] in seen_names:
                        continue
                    
                    v.setdefault('branch', 'US ARMY')
                    v.setdefault('death', '')
                    v.setdefault('url', '')
                    v.setdefault('cemetery', '')
                    
                    seen_names.add(v['name'])
                    all_veterans.append(v)
                    name_count += 1
                
                time.sleep(0.3)
        
        logger.info(f"  Found {name_count} veterans for '{surname}'")
        logger.info(f"  Total so far: {len(all_veterans)}")
        
        time.sleep(random.uniform(0.5, 1.5))
    
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
    print("VA GRAVE LOCATOR (NGL) SCRAPER v3")
    print("With pagination and expanded names")
    print("=" * 60)
    print()
    
    # Scrape
    veterans = scrape_all(max_per_name=50, max_total=2000, max_pages=5)
    
    print()
    print(f"Total veterans scraped: {len(veterans)}")
    
    # Save
    save_veterans(veterans)
    
    # Show sample
    print()
    print("Sample veterans:")
    for v in veterans[:5]:
        print(f"  - {v['name']}")
        print(f"    Birth: {v.get('birth', 'N/A')}, Death: {v.get('death', 'N/A')}, Branch: {v.get('branch', 'N/A')}")


if __name__ == "__main__":
    main()
