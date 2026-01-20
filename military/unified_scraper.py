"""
Unified Veterans Scraper - Under 70 years old
Scrape from ANC, VLM, NGL with expanded surname list
"""
import json
import random
import time
import re
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

# Output files
OUTPUT_DIR = Path(__file__).parent / "data"

# Minimum birth year (1955 = under 70)
MIN_BIRTH_YEAR = 1955

# API endpoints
EISS_BASE_URL = "https://ancexplorer.army.mil/proxy/proxy.ashx?https://wspublic.eiss.army.mil/v1/IssRetrieveServices.svc/search"
NGL_SEARCH_URL = "https://gravelocator.cem.va.gov/ngl/result"

# Expanded Common Names
COMMON_NAMES = [
    # --- Top 90+ ---
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
    "WATSON", "BROOKS", "CHAVEZ", "WOOD", "JAMES",
    "BENNETT", "GRAY", "MENDOZA", "RUIZ", "HUGHES",

    # --- Specific military records names ---
    "LA BELLE", "LARRY", "AARON",

    # --- Fallen Heroes surnames ---
    "SULLIVAN", "MCDONALD", "OWENS", "BRYANT", "SIMMONS",
    "FOSTER", "BUTLER", "HUNTER", "GRAHAM", "WALLACE",
    "ALVARADO", "CASTILLO", "ROMERO", "ESTRADA", "ORTEGA",
    "DELGADO", "RIOS", "VEGA", "WALSH", "MCCAULEY",
    "HARRINGTON", "O'CONNOR", "MCCARTHY", "PORTER", "PALMER",

    # --- Rural & Regular military surnames ---
    "ALEXANDER", "BARNES", "HENDERSON", "PATTERSON", "POWELL",
    "LONG", "PERRY", "HAYES", "JENKINS", "STEVENS",
    "WAGNER", "SCHMIDT", "SCHULTZ", "SNYDER", "O'BRIEN",
    "RYAN", "SANTIAGO", "VASQUEZ", "VARGAS", "BOYD",
    "GRIFFIN", "WEST", "MASON", "HOLT", "HALE",
    "BOONE", "BLAIR", "KENNEDY", "QUINN", "BURKE",
    "CASEY", "ROSSI", "DUBOIS", "LEBLANC", "PELTIER",
    "MARINO", "LOMBARDI", "WOLF", "KOCH", "KLINE"
]

BRANCH_MAP = {
    "USA": "US ARMY", "USN": "US NAVY", "USAF": "US AIR FORCE",
    "USMC": "US MARINE CORPS", "USCG": "US COAST GUARD",
    "US ARMY": "US ARMY", "US NAVY": "US NAVY",
    "US AIR FORCE": "US AIR FORCE", "US MARINE CORPS": "US MARINE CORPS",
    "ARMY": "US ARMY", "NAVY": "US NAVY", "AIR FORCE": "US AIR FORCE",
    "MARINE CORPS": "US MARINE CORPS",
    "": "US ARMY",
}

BRANCH_ORG = {
    "US ARMY": {"id": 4070, "name": "Army"},
    "US NAVY": {"id": 4072, "name": "Navy"},
    "US AIR FORCE": {"id": 4073, "name": "Air Force"},
    "US MARINE CORPS": {"id": 4071, "name": "Marine Corps"},
    "US COAST GUARD": {"id": 4074, "name": "Coast Guard"},
}


def parse_date_api(date_str: str) -> str:
    """Parse date from MM/DD/YYYY HH:MM to YYYY/MM/DD."""
    if not date_str:
        return ""
    try:
        parts = date_str.split(" ")[0]
        month, day, year = parts.split("/")
        return f"{year}/{month.zfill(2)}/{day.zfill(2)}"
    except:
        return ""


def get_birth_year(date_str: str) -> int:
    """Get year from YYYY/MM/DD."""
    if not date_str:
        return 0
    try:
        return int(date_str.split("/")[0])
    except:
        return 0


def gen_discharge() -> str:
    """Generate discharge date within 12 months."""
    days_ago = random.randint(30, 330)
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def clean_name(name: str) -> str:
    """Clean name."""
    if not name:
        return ""
    name = re.sub(r'^[\'\"\d~\-\s]+', '', name)
    name = re.sub(r'[\'\"\d~\-\s]+$', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip().upper()


# ===================== ANC SCRAPER =====================

def query_anc(surname: str, start: int = 0, limit: int = 100) -> List[Dict]:
    """Query ANC EISS API."""
    query = f"primarylastname~{surname}%2Ccemeteryid%3DALL"
    sort = "PrimaryLastName%2CPrimaryFirstName%2CPrimaryMiddleName%2CDOB%2CDOD"
    url = f"{EISS_BASE_URL}?AppId=Roi&q={query}&start={start}&limit={limit}&sortColumn={sort}&sortOrder=asc&f=json"
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("SearchResult", {}).get("Records", [])
    except Exception as e:
        logger.error(f"ANC request failed: {e}")
    return []


def parse_anc_record(record: Dict) -> Dict:
    """Parse ANC record."""
    first = record.get("PrimaryFirstName", "").strip().upper()
    middle = record.get("PrimaryMiddleName", "").strip().upper()
    last = record.get("PrimaryLastName", "").strip().upper()
    
    firstname = f"{first} {middle}".strip() if middle else first
    
    dob = parse_date_api(record.get("DOB", ""))
    dod = parse_date_api(record.get("DOD", ""))
    
    branch_code = record.get("BRANCHOFSERVICE", "").strip()
    branch = BRANCH_MAP.get(branch_code, "US ARMY")
    branch_info = BRANCH_ORG.get(branch, {"id": 4070, "name": "Army"})
    
    return {
        "name": f"{firstname} {last}".strip(),
        "firstname": firstname,
        "lastname": last,
        "branch": branch,
        "branch_id": branch_info["id"],
        "branch_name": branch_info["name"],
        "birth": dob,
        "death": dod,
        "discharge": gen_discharge(),
        "source": "ANC",
    }


def scrape_anc(max_per_name: int = 50, max_total: int = 2000) -> List[Dict]:
    """Scrape ANC for young veterans."""
    all_vets = []
    seen = set()
    
    logger.info(f"=== ANC SCRAPE (born >= {MIN_BIRTH_YEAR}) ===")
    
    for surname in COMMON_NAMES:
        if len(all_vets) >= max_total:
            break
        
        logger.info(f"ANC: {surname}...")
        
        start = 0
        count = 0
        
        while count < max_per_name and start < 500:
            records = query_anc(surname, start=start, limit=100)
            if not records:
                break
            
            for rec in records:
                if count >= max_per_name or len(all_vets) >= max_total:
                    break
                
                birth_year = get_birth_year(parse_date_api(rec.get("DOB", "")))
                if birth_year < MIN_BIRTH_YEAR:
                    continue
                
                vet = parse_anc_record(rec)
                if not vet["firstname"] or not vet["birth"]:
                    continue
                
                if vet["name"] in seen:
                    continue
                
                seen.add(vet["name"])
                all_vets.append(vet)
                count += 1
            
            start += 100
            time.sleep(0.3)
        
        if count > 0:
            logger.info(f"  Found {count} young")
        time.sleep(0.5)
    
    logger.info(f"ANC Total: {len(all_vets)}")
    return all_vets


# ===================== NGL SCRAPER =====================

def search_ngl(last_name: str) -> str:
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
    
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.post(NGL_SEARCH_URL, data=form_data)
            if response.status_code == 200:
                return response.text
    except:
        pass
    return ""


def parse_ngl_html(html: str) -> List[Dict]:
    """Parse NGL HTML."""
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
                if birth_year >= MIN_BIRTH_YEAR:
                    current['name'] = clean_name(current['name'])
                    if current['name']:
                        branch = current.get('branch', 'US ARMY')
                        branch_info = BRANCH_ORG.get(branch, {"id": 4070, "name": "Army"})
                        current['branch_id'] = branch_info['id']
                        current['branch_name'] = branch_info['name']
                        parts = current['name'].split()
                        if len(parts) >= 2:
                            current['lastname'] = parts[-1]
                            current['firstname'] = ' '.join(parts[:-1])
                        else:
                            current['lastname'] = current['name']
                            current['firstname'] = ''
                        current['discharge'] = gen_discharge()
                        current['source'] = 'NGL'
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
                        match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", value)
                        if match:
                            m, d, y = match.groups()
                            current['birth'] = f"{y}/{m.zfill(2)}/{d.zfill(2)}"
                    elif 'date of death' in header:
                        match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", value)
                        if match:
                            m, d, y = match.groups()
                            current['death'] = f"{y}/{m.zfill(2)}/{d.zfill(2)}"
                    elif 'rank' in header or 'branch' in header:
                        for key in BRANCH_ORG:
                            if key in value.upper():
                                current['branch'] = key
                                break
    
    return veterans


def scrape_ngl(max_per_name: int = 30, max_total: int = 1000) -> List[Dict]:
    """Scrape NGL for young veterans."""
    all_vets = []
    seen = set()
    
    logger.info(f"=== NGL SCRAPE (born >= {MIN_BIRTH_YEAR}) ===")
    
    for surname in COMMON_NAMES:
        if len(all_vets) >= max_total:
            break
        
        logger.info(f"NGL: {surname}...")
        
        html = search_ngl(surname)
        if html:
            veterans = parse_ngl_html(html)
            count = 0
            for v in veterans:
                if count >= max_per_name or len(all_vets) >= max_total:
                    break
                if v['name'] in seen:
                    continue
                seen.add(v['name'])
                all_vets.append(v)
                count += 1
            if count > 0:
                logger.info(f"  Found {count}")
        
        time.sleep(0.5)
    
    logger.info(f"NGL Total: {len(all_vets)}")
    return all_vets


# ===================== MAIN =====================

def main():
    print("=" * 60)
    print("  UNIFIED VETERANS SCRAPER - UNDER 70")
    print(f"  Filter: Born >= {MIN_BIRTH_YEAR}")
    print(f"  Surnames: {len(COMMON_NAMES)}")
    print("=" * 60)
    
    all_vets = []
    seen = set()
    
    # Phase 1: ANC
    print("\n[PHASE 1] ANC Explorer...")
    anc_vets = scrape_anc(max_per_name=30, max_total=1500)
    for v in anc_vets:
        if v['name'] not in seen:
            seen.add(v['name'])
            all_vets.append(v)
    print(f"After ANC: {len(all_vets)}")
    
    # Phase 2: NGL
    print("\n[PHASE 2] NGL Grave Locator...")
    ngl_vets = scrape_ngl(max_per_name=30, max_total=1000)
    for v in ngl_vets:
        if v['name'] not in seen:
            seen.add(v['name'])
            all_vets.append(v)
    print(f"After NGL: {len(all_vets)}")
    
    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "all_under70_veterans.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sorted(all_vets, key=lambda x: x['name']), f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 60}")
    print(f"TOTAL: {len(all_vets)} veterans under 70")
    print(f"Saved to: {output_file}")
    
    # Sample
    print("\nSample:")
    for v in all_vets[:5]:
        print(f"  {v['name']}: {v['birth']} ({v['source']})")


if __name__ == "__main__":
    main()
