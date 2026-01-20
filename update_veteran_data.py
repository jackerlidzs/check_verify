"""
Update all veteran data with discharge date and branch IDs
P0 Critical Fixes
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# Branch Organization IDs (from SheerID)
BRANCH_ORG_MAP = {
    "US ARMY": {"id": 4070, "name": "Army"},
    "US NAVY": {"id": 4072, "name": "Navy"},
    "US AIR FORCE": {"id": 4073, "name": "Air Force"},
    "US MARINE CORPS": {"id": 4071, "name": "Marine Corps"},
    "US COAST GUARD": {"id": 4074, "name": "Coast Guard"},
    "US SPACE FORCE": {"id": 4544268, "name": "Space Force"},
    # Aliases
    "ARMY": {"id": 4070, "name": "Army"},
    "NAVY": {"id": 4072, "name": "Navy"},
    "AIR FORCE": {"id": 4073, "name": "Air Force"},
    "MARINE CORPS": {"id": 4071, "name": "Marine Corps"},
    "COAST GUARD": {"id": 4074, "name": "Coast Guard"},
}

# Default branch
DEFAULT_BRANCH = {"id": 4070, "name": "Army"}


def generate_discharge_date() -> str:
    """Generate a random discharge date within last 11 months (safe margin)."""
    today = datetime.now()
    
    # Random days between 30 and 330 days ago (safe within 12 months)
    days_ago = random.randint(30, 330)
    discharge = today - timedelta(days=days_ago)
    
    return discharge.strftime("%Y-%m-%d")


def get_branch_info(branch_text: str) -> dict:
    """Get branch ID and name from branch text."""
    if not branch_text:
        return DEFAULT_BRANCH
    
    branch_upper = branch_text.upper().strip()
    
    # Direct match
    if branch_upper in BRANCH_ORG_MAP:
        return BRANCH_ORG_MAP[branch_upper]
    
    # Partial match
    for key, value in BRANCH_ORG_MAP.items():
        if key in branch_upper or branch_upper in key:
            return value
    
    return DEFAULT_BRANCH


def update_veteran_file(filepath: str):
    """Update a veteran data file with discharge date and branch IDs."""
    
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}")
        return
    
    print(f"\n=== Processing: {path.name} ===")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Records: {len(data)}")
    
    for record in data:
        # Add discharge date if missing
        if not record.get('discharge'):
            record['discharge'] = generate_discharge_date()
        
        # Add branch info
        branch_text = record.get('branch', '')
        branch_info = get_branch_info(branch_text)
        record['branch_id'] = branch_info['id']
        record['branch_name'] = branch_info['name']
    
    # Save
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Show sample
    print("Sample:")
    for r in data[:3]:
        print(f"  {r.get('name', '')[:25]:25} | branch: {r.get('branch_name', '')} ({r.get('branch_id', '')}) | discharge: {r.get('discharge', '')}")


if __name__ == "__main__":
    files = [
        'military/data/ngl_veterans.json',
        'military/data/anc_veterans.json', 
        'military/data/veterans_usa.json',
    ]
    
    for f in files:
        update_veteran_file(f)
    
    print("\n=== Summary ===")
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
            # Check fields
            sample = data[0] if data else {}
            has_discharge = 'discharge' in sample
            has_branch_id = 'branch_id' in sample
            print(f"{Path(f).name}: {len(data)} records | discharge: {'✅' if has_discharge else '❌'} | branch_id: {'✅' if has_branch_id else '❌'}")
        except Exception as e:
            print(f"{Path(f).name}: ERROR - {e}")
