"""
Remove veterans with incomplete first names (only initials)
Keep only records where firstname has at least one full name (3+ chars)
"""
import json
import re
from pathlib import Path


def has_full_firstname(firstname: str) -> bool:
    """Check if firstname has at least one full name (not just initials)."""
    if not firstname:
        return False
    
    parts = firstname.strip().split()
    
    # Check if at least one part is a real name (3+ chars)
    for part in parts:
        # Skip JR, SR, etc
        if part in ['JR', 'SR', 'II', 'III', 'IV', 'V']:
            continue
        # A real name should be 3+ characters
        if len(part) >= 3:
            return True
    
    return False


def filter_file(filepath: str):
    """Filter a veteran data file to keep only complete names."""
    
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}")
        return 0, 0
    
    print(f"\n=== Processing: {path.name} ===")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    original_count = len(data)
    
    # Filter - keep only records with full firstname
    filtered_data = []
    removed_examples = []
    
    for record in data:
        firstname = record.get('firstname', '')
        
        if has_full_firstname(firstname):
            filtered_data.append(record)
        else:
            if len(removed_examples) < 10:
                removed_examples.append(record.get('name', ''))
    
    removed_count = original_count - len(filtered_data)
    
    print(f"Original: {original_count}")
    print(f"Kept: {len(filtered_data)}")
    print(f"Removed: {removed_count}")
    
    if removed_examples:
        print("Removed examples:")
        for ex in removed_examples[:5]:
            print(f"  - {ex}")
    
    # Save
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, indent=2, ensure_ascii=False)
    
    # Show kept samples
    print("Kept samples:")
    for r in filtered_data[:5]:
        print(f"  - {r.get('name', '')} | fn: '{r.get('firstname', '')}'")
    
    return original_count, len(filtered_data)


if __name__ == "__main__":
    files = [
        'military/data/ngl_veterans.json',
        'military/data/anc_veterans.json', 
        'military/data/veterans_usa.json',
    ]
    
    total_original = 0
    total_kept = 0
    
    for f in files:
        orig, kept = filter_file(f)
        total_original += orig
        total_kept += kept
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total original: {total_original}")
    print(f"Total kept: {total_kept}")
    print(f"Total removed: {total_original - total_kept}")
    print(f"Removal rate: {(total_original - total_kept) / total_original * 100:.1f}%")
