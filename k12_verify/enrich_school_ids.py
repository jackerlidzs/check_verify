"""
Enrich teacher data with SheerID school IDs

This script:
1. Reads k12_teacher_info.json
2. For each unique school, calls SheerID API to get school ID
3. Adds sheerid_school_id and sheerid_school_type to each teacher
4. Filters to only include HIGH_SCHOOL type (not K12)
5. Saves enriched data

Usage:
    python enrich_school_ids.py
"""
import json
import httpx
from pathlib import Path
from collections import defaultdict

# SheerID School Search API (discovered via browser intercept)
SCHOOL_SEARCH_API = "https://orgsearch.sheerid.net/rest/organization/search"
SCHOOL_SEARCH_ACCOUNT_ID = "67d1dd27d7732a41eb64d141"  # ChatGPT program ID


def search_school_api(school_name: str, city: str = None, state: str = None, country: str = "US"):
    """
    Search for school using SheerID API directly.
    STRICT: Only returns K12 type, skip HIGH_SCHOOL entirely.
    
    Returns:
        Dict with school id, name, type or None if not found (or only HIGH_SCHOOL)
    """
    try:
        # Build search query
        search_query = school_name
        if city:
            search_query += f" {city}"
        if state:
            search_query += f", {state}"
        
        params = {
            "accountId": SCHOOL_SEARCH_ACCOUNT_ID,
            "country": country,
            "name": search_query,
            "tags": "qualifying_hs,qualifying_k12",
            "type": "K12,HIGH_SCHOOL",
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        with httpx.Client(timeout=10) as client:
            response = client.get(SCHOOL_SEARCH_API, params=params, headers=headers)
            
            if response.status_code == 200:
                schools = response.json()
                if schools and len(schools) > 0:
                    # STRICT: Only return K12 type, never HIGH_SCHOOL
                    for school in schools:
                        if school.get('type') == 'K12':
                            return school
                    
                    # No K12 found - skip HIGH_SCHOOL
                    print(f"  [SKIP] Only HIGH_SCHOOL found, no K12")
                    return None
        
        return None
    except Exception as e:
        print(f"  Error searching for {school_name}: {e}")
        return None


def main():
    # Load teacher data
    data_file = Path(__file__).parent / "app" / "core" / "data" / "k12_teacher_info.json"
    
    if not data_file.exists():
        print(f"File not found: {data_file}")
        return
    
    with open(data_file, 'r', encoding='utf-8') as f:
        teacher_data = json.load(f)
    
    print(f"Loaded teacher data from {data_file}")
    
    # Collect unique schools
    unique_schools = {}  # school_name -> {city, state}
    
    for district, teachers in teacher_data.items():
        for teacher in teachers:
            school_name = teacher.get('school_name', '')
            if school_name:
                key = f"{school_name}|{teacher.get('school_city', '')}|{teacher.get('school_state', '')}"
                if key not in unique_schools:
                    unique_schools[key] = {
                        'name': school_name,
                        'city': teacher.get('school_city', ''),
                        'state': teacher.get('school_state', ''),
                    }
    
    print(f"\nFound {len(unique_schools)} unique schools")
    
    # Look up each school
    school_id_map = {}  # key -> sheerid data
    
    for i, (key, school) in enumerate(unique_schools.items()):
        print(f"\n[{i+1}/{len(unique_schools)}] Looking up: {school['name']} ({school['city']}, {school['state']})")
        
        result = search_school_api(
            school['name'],
            school['city'],
            school['state']
        )
        
        if result:
            school_id_map[key] = {
                'sheerid_school_id': result.get('id'),
                'sheerid_school_name': result.get('name'),
                'sheerid_school_type': result.get('type'),  # HIGH_SCHOOL or K12
            }
            print(f"  -> ID: {result.get('id')}, Type: {result.get('type')}")
        else:
            print(f"  -> NOT FOUND")
    
    print(f"\n\nFound SheerID data for {len(school_id_map)}/{len(unique_schools)} schools")
    
    # Enrich teacher data
    enriched = {}
    k12_count = 0
    high_school_count = 0
    total_teachers = 0
    
    for district, teachers in teacher_data.items():
        enriched[district] = []
        
        for teacher in teachers:
            total_teachers += 1
            school_name = teacher.get('school_name', '')
            key = f"{school_name}|{teacher.get('school_city', '')}|{teacher.get('school_state', '')}"
            
            if key in school_id_map:
                school_data = school_id_map[key]
                teacher.update(school_data)
                enriched[district].append(teacher)
                
                # Count by type
                if school_data.get('sheerid_school_type') == 'K12':
                    k12_count += 1
                else:
                    high_school_count += 1
            else:
                # Keep teacher but no SheerID data
                enriched[district].append(teacher)
    
    print(f"\n\nStats:")
    print(f"  Total teachers: {total_teachers}")
    print(f"  K12 type: {k12_count}")
    print(f"  HIGH_SCHOOL type: {high_school_count}")
    
    # Save enriched data
    output_file = data_file.parent / "k12_teacher_info_enriched.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved enriched data to: {output_file}")
    
    # Also show sample
    print("\n\nSample enriched teacher:")
    for district, teachers in enriched.items():
        for teacher in teachers[:1]:
            if 'sheerid_school_id' in teacher:
                print(json.dumps(teacher, indent=2))
                return


if __name__ == "__main__":
    main()
