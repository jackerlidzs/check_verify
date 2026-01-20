"""
Fix firstname - remove leading initials if followed by full name
"A AARON" -> "AARON"
"A B CHARLES" -> "CHARLES" 
"AARON" -> "AARON" (no change)
"""
import json
import re
from pathlib import Path


def fix_firstname(firstname: str) -> str:
    """Remove leading initials, keep the full name part."""
    if not firstname:
        return ""
    
    parts = firstname.strip().split()
    
    if not parts:
        return ""
    
    # Find the first full name (3+ chars, not a suffix)
    suffixes = {'JR', 'SR', 'II', 'III', 'IV', 'V'}
    
    result_parts = []
    found_real_name = False
    
    for part in parts:
        # Skip suffixes
        if part in suffixes:
            continue
        
        # If it's a real name (3+ chars)
        if len(part) >= 3:
            found_real_name = True
            result_parts.append(part)
        elif found_real_name:
            # Keep initials after a real name (middle initials)
            result_parts.append(part)
        # Skip initials before the first real name
    
    return " ".join(result_parts)


def fix_file(filepath: str):
    """Fix firstname in a veteran data file."""
    
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}")
        return
    
    print(f"\n=== Processing: {path.name} ===")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Records: {len(data)}")
    
    changes = 0
    
    for record in data:
        old_firstname = record.get('firstname', '')
        new_firstname = fix_firstname(old_firstname)
        
        if new_firstname != old_firstname:
            changes += 1
            
            # Update firstname
            record['firstname'] = new_firstname
            
            # Update full name
            lastname = record.get('lastname', '')
            if new_firstname:
                record['name'] = f"{new_firstname} {lastname}"
            else:
                record['name'] = lastname
    
    print(f"Changed: {changes}")
    
    # Save
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Show samples
    print("Samples:")
    for r in data[:8]:
        print(f"  {r.get('name', '')[:35]:35} | fn: '{r.get('firstname', '')}'")


if __name__ == "__main__":
    files = [
        'military/data/ngl_veterans.json',
        'military/data/anc_veterans.json', 
        'military/data/veterans_usa.json',
    ]
    
    for f in files:
        fix_file(f)
    
    print("\n=== DONE ===")
