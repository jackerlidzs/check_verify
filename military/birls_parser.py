"""
BIRLS Database Parser
Download and process BIRLS data for recent discharges (within 12 months)
Source: https://archive.org/details/BIRLS_database (Reclaim The Records)
"""
import csv
import json
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Output
OUTPUT_FILE = Path(__file__).parent / "data" / "birls_veterans.json"

# Download URLs (from Internet Archive)
BIRLS_MAIN_URL = "https://archive.org/download/BIRLS_database/Reclaim_The_Records_-_BIRLS_database_-_file_received_from_the_VA_mid-2022.csv"
BIRLS_UPDATE_URL = "https://archive.org/download/BIRLS_database/Reclaim_The_Records_-_BIRLS_database_-_update_file_received_from_the_VA_for_2020-2023.csv"

# Local cache paths
DATA_DIR = Path(__file__).parent / "data"
BIRLS_MAIN_FILE = DATA_DIR / "birls_main.csv"
BIRLS_UPDATE_FILE = DATA_DIR / "birls_update_2020_2023.csv"

# 12 month window
CUTOFF_DATE = datetime.now() - timedelta(days=365)

# Branch mapping
BRANCH_MAP = {
    "ARMY": {"id": 4070, "name": "Army"},
    "USA": {"id": 4070, "name": "Army"},
    "NAVY": {"id": 4072, "name": "Navy"},
    "USN": {"id": 4072, "name": "Navy"},
    "AIR FORCE": {"id": 4073, "name": "Air Force"},
    "USAF": {"id": 4073, "name": "Air Force"},
    "AAF": {"id": 4073, "name": "Air Force"},  # Army Air Forces
    "MARINE": {"id": 4071, "name": "Marine Corps"},
    "USMC": {"id": 4071, "name": "Marine Corps"},
    "COAST GUARD": {"id": 4074, "name": "Coast Guard"},
    "USCG": {"id": 4074, "name": "Coast Guard"},
}


def download_file(url: str, local_path: Path) -> bool:
    """Download file if not cached."""
    if local_path.exists():
        size_mb = local_path.stat().st_size / (1024 * 1024)
        logger.info(f"Using cached file: {local_path.name} ({size_mb:.1f} MB)")
        return True
    
    logger.info(f"Downloading: {url}")
    logger.info(f"This may take a while (file is large)...")
    
    try:
        urllib.request.urlretrieve(url, local_path)
        size_mb = local_path.stat().st_size / (1024 * 1024)
        logger.info(f"Downloaded: {local_path.name} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date from BIRLS format."""
    if not date_str or date_str.strip() == "":
        return None
    
    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except:
            pass
    
    # Try extracting year-month-day from string
    try:
        parts = date_str.replace("/", "-").split("-")
        if len(parts) == 3:
            # Assume YYYY-MM-DD or similar
            year = int(parts[0]) if len(parts[0]) == 4 else int(parts[2])
            month = int(parts[1])
            day = int(parts[2]) if len(parts[0]) == 4 else int(parts[0])
            return datetime(year, month, day)
    except:
        pass
    
    return None


def get_branch_info(branch_str: str) -> Dict:
    """Map branch string to SheerID format."""
    if not branch_str:
        return {"id": 4070, "name": "Army"}
    
    branch_upper = branch_str.upper().strip()
    
    for key, value in BRANCH_MAP.items():
        if key in branch_upper:
            return value
    
    return {"id": 4070, "name": "Army"}


def process_csv(csv_path: Path, cutoff_date: datetime) -> List[Dict]:
    """Process BIRLS CSV and filter for recent discharges."""
    veterans = []
    
    if not csv_path.exists():
        logger.error(f"File not found: {csv_path}")
        return veterans
    
    logger.info(f"Processing: {csv_path.name}")
    
    # First, detect the CSV structure
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        logger.info(f"CSV headers: {headers[:10]}...")
    
    # Column name mappings (try multiple possible names)
    first_name_cols = ['first_name', 'firstname', 'first', 'fname', 'FIRST_NAME']
    last_name_cols = ['last_name', 'lastname', 'last', 'lname', 'LAST_NAME']
    birth_cols = ['birth_date', 'birthdate', 'dob', 'date_of_birth', 'BIRTH_DATE', 'DOB']
    death_cols = ['death_date', 'deathdate', 'dod', 'date_of_death', 'DEATH_DATE', 'DOD']
    release_cols = ['release_date', 'releasedate', 'separation_date', 'discharge_date', 'RELEASE_DATE', 'SEPARATION_DATE']
    branch_cols = ['branch', 'branch_of_service', 'service_branch', 'BRANCH', 'SERVICE']
    
    def find_col(row: Dict, candidates: List[str]) -> str:
        for col in candidates:
            if col in row and row[col]:
                return row[col]
            if col.lower() in [k.lower() for k in row.keys()]:
                for k in row.keys():
                    if k.lower() == col.lower():
                        return row[k]
        return ""
    
    count = 0
    recent_count = 0
    
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            count += 1
            
            if count % 100000 == 0:
                logger.info(f"  Processed {count:,} rows, found {recent_count} recent...")
            
            # Get release/discharge date
            release_str = find_col(row, release_cols)
            release_date = parse_date(release_str)
            
            if not release_date:
                continue
            
            # Check if within 12 months
            if release_date < cutoff_date:
                continue
            
            # Get other fields
            first_name = find_col(row, first_name_cols).strip().upper()
            last_name = find_col(row, last_name_cols).strip().upper()
            birth_str = find_col(row, birth_cols)
            death_str = find_col(row, death_cols)
            branch_str = find_col(row, branch_cols)
            
            if not first_name or not last_name:
                continue
            
            # Parse dates
            birth_date = parse_date(birth_str)
            death_date = parse_date(death_str)
            
            if not birth_date:
                continue
            
            # Calculate age
            age = (datetime.now() - birth_date).days // 365
            if age > 100 or age < 18:
                continue
            
            branch_info = get_branch_info(branch_str)
            
            veteran = {
                "firstname": first_name,
                "lastname": last_name,
                "name": f"{first_name} {last_name}",
                "birth": birth_date.strftime("%Y/%m/%d"),
                "death": death_date.strftime("%Y/%m/%d") if death_date else "",
                "discharge": release_date.strftime("%Y-%m-%d"),
                "branch": f"US {branch_info['name'].upper()}",
                "branch_id": branch_info["id"],
                "branch_name": branch_info["name"],
                "source": "BIRLS",
            }
            
            veterans.append(veteran)
            recent_count += 1
    
    logger.info(f"  Total processed: {count:,}")
    logger.info(f"  Recent discharges: {recent_count}")
    
    return veterans


def main():
    print("=" * 70)
    print("  BIRLS DATABASE PARSER")
    print(f"  Looking for discharges after: {CUTOFF_DATE.strftime('%Y-%m-%d')}")
    print("=" * 70)
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    all_veterans = []
    seen = set()
    
    # Process update file first (more recent data)
    print("\n[1/2] Processing 2020-2023 update file...")
    
    if BIRLS_UPDATE_FILE.exists() or download_file(BIRLS_UPDATE_URL, BIRLS_UPDATE_FILE):
        veterans = process_csv(BIRLS_UPDATE_FILE, CUTOFF_DATE)
        for v in veterans:
            key = f"{v['firstname']}|{v['lastname']}|{v['birth']}"
            if key not in seen:
                seen.add(key)
                all_veterans.append(v)
    
    # Process main file (if needed more data)
    if len(all_veterans) < 100:
        print("\n[2/2] Processing main file...")
        if BIRLS_MAIN_FILE.exists() or download_file(BIRLS_MAIN_URL, BIRLS_MAIN_FILE):
            veterans = process_csv(BIRLS_MAIN_FILE, CUTOFF_DATE)
            for v in veterans:
                key = f"{v['firstname']}|{v['lastname']}|{v['birth']}"
                if key not in seen:
                    seen.add(key)
                    all_veterans.append(v)
    
    # Save results
    print()
    print("=" * 70)
    print(f"  TOTAL FOUND: {len(all_veterans)} veterans with recent discharge")
    print("=" * 70)
    
    if all_veterans:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(sorted(all_veterans, key=lambda x: x['name']), f, indent=2, ensure_ascii=False)
        print(f"Saved to: {OUTPUT_FILE}")
        
        print("\nSample:")
        for v in all_veterans[:5]:
            print(f"  {v['name']}")
            print(f"    Birth: {v['birth']}, Discharge: {v['discharge']}")
    else:
        print("\nNo veterans found with discharge within 12 months.")
        print("This is expected - BIRLS contains deceased veterans,")
        print("and recently deceased veterans are rare.")


if __name__ == "__main__":
    main()
