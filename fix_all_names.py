"""
Fix ALL veteran data - add firstname/lastname fields
Works for NGL, ANC, and VLM data
"""
import json
import re
from pathlib import Path

# Suffixes that should be at end of lastname
SUFFIXES = {'JR', 'SR', 'II', 'III', 'IV', 'V'}

def parse_name(full_name: str) -> dict:
    """Parse full name into firstname and lastname."""
    if not full_name:
        return {"firstname": "", "lastname": ""}
    
    name = full_name.strip().upper()
    name = re.sub(r'\s+', ' ', name)
    
    parts = name.split()
    
    if len(parts) == 0:
        return {"firstname": "", "lastname": ""}
    
    if len(parts) == 1:
        return {"firstname": "", "lastname": parts[0]}
    
    # Extract suffix
    suffix = ""
    new_parts = []
    for p in parts:
        if p in SUFFIXES:
            suffix = p
        else:
            new_parts.append(p)
    parts = new_parts
    
    if len(parts) == 0:
        return {"firstname": "", "lastname": suffix}
    
    if len(parts) == 1:
        lastname = parts[0]
        if suffix:
            lastname = f"{lastname} {suffix}"
        return {"firstname": "", "lastname": lastname}
    
    # Last part is lastname, rest is firstname
    lastname = parts[-1]
    firstname_parts = parts[:-1]
    firstname = " ".join(firstname_parts)
    
    if suffix:
        lastname = f"{lastname} {suffix}"
    
    return {"firstname": firstname, "lastname": lastname}


def clean_name_field(name: str) -> str:
    """Clean a name field."""
    if not name:
        return ""
    
    name = re.sub(r'^[^A-Za-z]+', '', name)
    name = re.sub(r'[^A-Za-z]+$', '', name)
    name = re.sub(r'[^A-Za-z\s\'\-]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name.upper()


def fix_file(filepath: str):
    """Fix a veteran data file."""
    
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}")
        return
    
    print(f"\n=== Processing: {path.name} ===")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Original records: {len(data)}")
    
    fixed_data = []
    
    for record in data:
        old_name = record.get('name', '')
        
        parsed = parse_name(old_name)
        firstname = clean_name_field(parsed['firstname'])
        lastname = clean_name_field(parsed['lastname'])
        
        if not lastname:
            continue
        
        # Build new name
        if firstname:
            new_name = f"{firstname} {lastname}"
        else:
            new_name = lastname
        
        record['name'] = new_name
        record['firstname'] = firstname
        record['lastname'] = lastname
        
        fixed_data.append(record)
    
    print(f"Fixed records: {len(fixed_data)}")
    
    # Save
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(fixed_data, f, indent=2, ensure_ascii=False)
    
    # Show samples
    print("Sample:")
    for r in fixed_data[:5]:
        fn = r.get('firstname', '')
        ln = r.get('lastname', '')
        print(f"  {r['name'][:30]:30} | fn: '{fn[:15]:15}' | ln: '{ln}'")


if __name__ == "__main__":
    files = [
        'military/data/ngl_veterans.json',
        'military/data/anc_veterans.json', 
        'military/data/veterans_usa.json',
    ]
    
    for f in files:
        fix_file(f)
    
    print("\n=== Summary ===")
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
            print(f"{Path(f).name}: {len(data)} records")
        except:
            print(f"{Path(f).name}: ERROR")
