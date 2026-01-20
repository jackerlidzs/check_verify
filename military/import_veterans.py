"""
Import Veterans Data from Manual Input File
Converts real_veterans.txt to JSON format for verification
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path(__file__).parent / "data"
INPUT_FILE = DATA_DIR / "real_veterans.txt"
OUTPUT_FILE = DATA_DIR / "real_veterans.json"

# 12 month window
CUTOFF_DATE = datetime.now() - timedelta(days=365)

# Branch mapping to SheerID format
BRANCH_MAP = {
    "ARMY": {"id": 4070, "name": "Army", "full": "US ARMY"},
    "US ARMY": {"id": 4070, "name": "Army", "full": "US ARMY"},
    "NAVY": {"id": 4072, "name": "Navy", "full": "US NAVY"},
    "US NAVY": {"id": 4072, "name": "Navy", "full": "US NAVY"},
    "AIR FORCE": {"id": 4073, "name": "Air Force", "full": "US AIR FORCE"},
    "US AIR FORCE": {"id": 4073, "name": "Air Force", "full": "US AIR FORCE"},
    "MARINES": {"id": 4071, "name": "Marine Corps", "full": "US MARINE CORPS"},
    "MARINE CORPS": {"id": 4071, "name": "Marine Corps", "full": "US MARINE CORPS"},
    "US MARINE CORPS": {"id": 4071, "name": "Marine Corps", "full": "US MARINE CORPS"},
    "COAST GUARD": {"id": 4074, "name": "Coast Guard", "full": "US COAST GUARD"},
    "US COAST GUARD": {"id": 4074, "name": "Coast Guard", "full": "US COAST GUARD"},
}


def parse_date(date_str: str) -> datetime:
    """Parse date from YYYY-MM-DD format."""
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d-%m-%Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except:
            pass
    
    raise ValueError(f"Cannot parse date: {date_str}")


def get_branch_info(branch_str: str) -> dict:
    """Get branch info for SheerID."""
    branch_upper = branch_str.upper().strip()
    
    if branch_upper in BRANCH_MAP:
        return BRANCH_MAP[branch_upper]
    
    # Try partial match
    for key, value in BRANCH_MAP.items():
        if key in branch_upper or branch_upper in key:
            return value
    
    # Default to Army
    logger.warning(f"Unknown branch '{branch_str}', defaulting to Army")
    return BRANCH_MAP["ARMY"]


def import_veterans():
    """Import veterans from text file."""
    if not INPUT_FILE.exists():
        logger.error(f"Input file not found: {INPUT_FILE}")
        logger.info("Create the file and add veteran data in format:")
        logger.info("firstName|lastName|branch|birthDate|dischargeDate")
        return []
    
    veterans = []
    errors = []
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('|')
            
            if len(parts) != 5:
                errors.append(f"Line {line_num}: Expected 5 fields, got {len(parts)}")
                continue
            
            first_name, last_name, branch, birth_str, discharge_str = parts
            
            try:
                # Parse dates
                birth_date = parse_date(birth_str)
                discharge_date = parse_date(discharge_str)
                
                # Validate discharge date (within 12 months)
                if discharge_date < CUTOFF_DATE:
                    errors.append(f"Line {line_num}: Discharge date {discharge_str} is older than 12 months")
                    continue
                
                # Get branch info
                branch_info = get_branch_info(branch)
                
                veteran = {
                    "firstname": first_name.strip().upper(),
                    "lastname": last_name.strip().upper(),
                    "name": f"{first_name.strip().upper()} {last_name.strip().upper()}",
                    "birth": birth_date.strftime("%Y/%m/%d"),
                    "discharge": discharge_date.strftime("%Y-%m-%d"),
                    "branch": branch_info["full"],
                    "branch_id": branch_info["id"],
                    "branch_name": branch_info["name"],
                    "source": "MANUAL",
                }
                
                veterans.append(veteran)
                logger.info(f"  ✓ {veteran['name']} - {veteran['branch']} - Discharged: {veteran['discharge']}")
                
            except Exception as e:
                errors.append(f"Line {line_num}: {str(e)}")
    
    return veterans, errors


def main():
    print("=" * 60)
    print("  IMPORT REAL VETERANS DATA")
    print("=" * 60)
    print(f"Input: {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Cutoff date: {CUTOFF_DATE.strftime('%Y-%m-%d')} (12 months ago)")
    print()
    
    veterans, errors = import_veterans()
    
    # Print errors
    if errors:
        print("\n⚠️  Errors:")
        for err in errors:
            print(f"  {err}")
    
    # Save results
    if veterans:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(veterans, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Imported {len(veterans)} veterans")
        print(f"Saved to: {OUTPUT_FILE}")
        
        print("\nSample:")
        for v in veterans[:3]:
            print(f"  {v['name']}: {v['birth']} | Discharge: {v['discharge']}")
    else:
        print("\n❌ No valid veterans data found")
        print("Add data to real_veterans.txt in format:")
        print("firstName|lastName|branch|birthDate|dischargeDate")


if __name__ == "__main__":
    main()
