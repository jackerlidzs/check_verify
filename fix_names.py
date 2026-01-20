"""
Fix NGL name format - split into firstname and lastname
Handle JR/SR/II/III/IV suffixes correctly
"""
import json
import re

# Suffixes that should be at end of lastname
SUFFIXES = {'JR', 'SR', 'II', 'III', 'IV', 'V'}

def parse_name(full_name: str) -> dict:
    """
    Parse full name into firstname and lastname.
    Input format: "FIRSTNAME MIDDLENAME LASTNAME" or "F M LASTNAME"
    Output: {"firstname": "...", "lastname": "..."}
    """
    if not full_name:
        return {"firstname": "", "lastname": ""}
    
    # Clean the name
    name = full_name.strip().upper()
    name = re.sub(r'\s+', ' ', name)
    
    parts = name.split()
    
    if len(parts) == 0:
        return {"firstname": "", "lastname": ""}
    
    if len(parts) == 1:
        # Only one part - assume it's lastname
        return {"firstname": "", "lastname": parts[0]}
    
    # Extract suffix if present (JR, SR, II, III, IV)
    suffix = ""
    for i, p in enumerate(parts):
        if p in SUFFIXES:
            suffix = p
            parts = parts[:i] + parts[i+1:]  # Remove suffix from parts
            break
    
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
    
    # Join firstname parts
    firstname = " ".join(firstname_parts)
    
    # Add suffix to lastname
    if suffix:
        lastname = f"{lastname} {suffix}"
    
    return {"firstname": firstname, "lastname": lastname}


def clean_name_field(name: str) -> str:
    """Clean a name field - remove invalid characters."""
    if not name:
        return ""
    
    # Remove leading/trailing non-alpha
    name = re.sub(r'^[^A-Za-z]+', '', name)
    name = re.sub(r'[^A-Za-z]+$', '', name)
    
    # Allow letters, spaces, hyphens, apostrophes
    name = re.sub(r'[^A-Za-z\s\'\-]', '', name)
    
    # Clean multiple spaces
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name.upper()


def fix_ngl_data():
    """Fix all NGL data."""
    
    # Load data
    with open('military/data/ngl_veterans.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Original records: {len(data)}")
    
    fixed_data = []
    invalid_count = 0
    
    for record in data:
        old_name = record.get('name', '')
        
        # Parse name
        parsed = parse_name(old_name)
        firstname = clean_name_field(parsed['firstname'])
        lastname = clean_name_field(parsed['lastname'])
        
        # Skip if no lastname
        if not lastname:
            invalid_count += 1
            continue
        
        # Build new name (FIRSTNAME LASTNAME format)
        if firstname:
            new_name = f"{firstname} {lastname}"
        else:
            new_name = lastname
        
        # Update record
        record['name'] = new_name
        record['firstname'] = firstname
        record['lastname'] = lastname
        
        fixed_data.append(record)
    
    print(f"Fixed records: {len(fixed_data)}")
    print(f"Invalid/removed: {invalid_count}")
    
    # Save
    with open('military/data/ngl_veterans.json', 'w', encoding='utf-8') as f:
        json.dump(fixed_data, f, indent=2, ensure_ascii=False)
    
    # Show samples
    print()
    print("Sample fixed names:")
    for r in fixed_data[:15]:
        fn = r.get('firstname', '')
        ln = r.get('lastname', '')
        print(f"  {r['name']} | fn: '{fn}' | ln: '{ln}'")
    
    # Show JR/SR examples
    print()
    print("JR/SR examples:")
    jr_examples = [r for r in fixed_data if 'JR' in r.get('lastname', '') or 'SR' in r.get('lastname', '')]
    for r in jr_examples[:10]:
        print(f"  {r['name']} | fn: '{r.get('firstname', '')}' | ln: '{r.get('lastname', '')}'")


if __name__ == "__main__":
    fix_ngl_data()
