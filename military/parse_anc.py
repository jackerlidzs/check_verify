"""
Parse raw ANC data into standard format
"""
import json
import re
from pathlib import Path

# Input/Output files
INPUT_FILE = Path(__file__).parent / "data" / "anc_veterans.json"
OUTPUT_FILE = Path(__file__).parent / "data" / "anc_veterans_parsed.json"

# Branch mapping
BRANCH_MAP = {
    "army": "US ARMY",
    "navy": "US NAVY",
    "air force": "US AIR FORCE",
    "marine": "US MARINE CORPS",
    "coast guard": "US COAST GUARD",
}


def parse_raw_veteran(raw_data):
    """Parse raw veteran data."""
    if isinstance(raw_data, dict) and "raw" in raw_data:
        text = raw_data["raw"]
    elif isinstance(raw_data, dict) and "name" in raw_data:
        text = raw_data.get("name", "")
    else:
        text = str(raw_data)
    
    # Clean up
    text = text.replace("\n", " ").strip()
    
    # Extract name (usually first part before cemetery)
    parts = text.split(",")
    if len(parts) >= 2:
        last_name = parts[0].strip()
        # First name is second part, stop at cemetery info
        first_part = parts[1].strip()
        first_name = first_part.split()[0] if first_part else ""
        
        # Handle middle initial
        first_parts = first_part.split()
        if len(first_parts) >= 2 and len(first_parts[1]) == 1:
            first_name = f"{first_parts[0]} {first_parts[1]}"
        
        name = f"{first_name} {last_name}".strip()
    else:
        name = text.split()[0] if text else "Unknown"
    
    # Detect branch from text
    branch = "US ARMY"  # Default
    text_lower = text.lower()
    if "navy" in text_lower:
        branch = "US NAVY"
    elif "air force" in text_lower:
        branch = "US AIR FORCE"
    elif "marine" in text_lower:
        branch = "US MARINE CORPS"
    elif "coast guard" in text_lower:
        branch = "US COAST GUARD"
    
    return {
        "branch": branch,
        "name": name.upper(),
        "birth": "",
        "death": "",
        "url": ""
    }


def main():
    """Parse ANC veterans data."""
    print("=" * 60)
    print("PARSE ANC VETERANS DATA")
    print("=" * 60)
    print()
    
    # Load raw data
    if not INPUT_FILE.exists():
        print(f"[ERROR] File not found: {INPUT_FILE}")
        return 1
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    print(f"Loaded {len(raw_data)} raw records")
    
    # Parse each record
    parsed = []
    for item in raw_data:
        try:
            veteran = parse_raw_veteran(item)
            if veteran["name"] and veteran["name"] != "Unknown":
                parsed.append(veteran)
        except Exception as e:
            print(f"  Error parsing: {e}")
    
    print(f"Parsed {len(parsed)} veterans")
    
    # Remove duplicates
    seen = set()
    unique = []
    for v in parsed:
        if v["name"] not in seen:
            seen.add(v["name"])
            unique.append(v)
    
    print(f"Unique: {len(unique)} veterans")
    
    # Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    
    print(f"Saved to: {OUTPUT_FILE}")
    
    # Show sample
    print()
    print("Sample:")
    for v in unique[:5]:
        print(f"  {v['branch']}: {v['name']}")
    
    return 0


if __name__ == "__main__":
    main()
