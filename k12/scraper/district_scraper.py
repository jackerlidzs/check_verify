"""
Large District Teacher Scraper
Specialized scraper for large US school districts with known email patterns.

Supported Districts:
- Miami-Dade County Public Schools (dadeschools.net)
- Los Angeles Unified School District (lausd.net)
- NYC Department of Education (schools.nyc.gov)

Usage:
    python district_scraper.py --district miami-dade --schools 5
    python district_scraper.py --district lausd --schools 5
    python district_scraper.py --list
"""

import json
import random
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
TEACHERS_FILE = DATA_DIR / "real_teachers.json"

# District configurations
DISTRICTS = {
    "miami-dade": {
        "name": "Miami-Dade County Public Schools",
        "domain": "dadeschools.net",
        "email_pattern": "firstinitial_lastname",  # e.g., jsmith@dadeschools.net
        "state": "FL",
        "schools": [
            {"id": "5901", "name": "South Dade Middle School", "city": "Homestead"},
            {"id": "7061", "name": "Miami Lakes Educational Center", "city": "Miami Lakes"},
            {"id": "6661", "name": "Coral Gables Senior High", "city": "Coral Gables"},
            {"id": "7281", "name": "Miami Palmetto Senior High", "city": "Pinecrest"},
            {"id": "7481", "name": "South Miami Senior High", "city": "South Miami"},
            {"id": "7001", "name": "Miami Beach Senior High", "city": "Miami Beach"},
            {"id": "6841", "name": "Hialeah Senior High", "city": "Hialeah"},
            {"id": "6801", "name": "Homestead Senior High", "city": "Homestead"},
        ],
    },
    "lausd": {
        "name": "Los Angeles Unified School District",
        "domain": "lausd.net",
        "email_pattern": "firstname_dot_lastname",  # e.g., john.smith@lausd.net
        "state": "CA",
        "schools": [
            {"id": "1001", "name": "Los Angeles High School", "city": "Los Angeles"},
            {"id": "1002", "name": "Hollywood High School", "city": "Los Angeles"},
            {"id": "1003", "name": "Fairfax High School", "city": "Los Angeles"},
            {"id": "1004", "name": "Venice High School", "city": "Los Angeles"},
            {"id": "1005", "name": "Lincoln High School", "city": "Los Angeles"},
        ],
    },
    "nyc-doe": {
        "name": "NYC Department of Education",
        "domain": "schools.nyc.gov",
        "email_pattern": "firstname_dot_lastname",  # e.g., john.smith@schools.nyc.gov
        "state": "NY",
        "schools": [
            {"id": "02M475", "name": "Stuyvesant High School", "city": "New York"},
            {"id": "05M670", "name": "Bronx High School of Science", "city": "Bronx"},
            {"id": "28Q687", "name": "Queens High School for Sciences", "city": "Jamaica"},
            {"id": "14K449", "name": "Brooklyn Technical High School", "city": "Brooklyn"},
            {"id": "02M475", "name": "High School of American Studies", "city": "Bronx"},
        ],
    },
}


def load_existing_teachers() -> List[Dict]:
    """Load existing teachers from JSON file."""
    if TEACHERS_FILE.exists():
        with open(TEACHERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_teachers(teachers: List[Dict]):
    """Save teachers to JSON file."""
    with open(TEACHERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(teachers, f, indent=4, ensure_ascii=False)
    logger.info(f"Saved {len(teachers)} teachers to {TEACHERS_FILE}")


def generate_email(first_name: str, last_name: str, pattern: str, domain: str) -> str:
    """Generate email based on district pattern."""
    first = first_name.lower().strip()
    last = last_name.lower().strip().replace(" ", "").replace("-", "")
    
    if pattern == "firstinitial_lastname":
        # jsmith@domain
        return f"{first[0]}{last}@{domain}"
    elif pattern == "firstname_dot_lastname":
        # john.smith@domain
        return f"{first}.{last}@{domain}"
    elif pattern == "firstname_lastname":
        # johnsmith@domain
        return f"{first}{last}@{domain}"
    else:
        # Default: first.last
        return f"{first}.{last}@{domain}"


def generate_birth_date(hire_year: int = None) -> str:
    """Generate realistic birth date. Target age: 30-45."""
    current_year = datetime.now().year
    
    if hire_year:
        age_at_hire = random.randint(25, 35)
        birth_year = hire_year - age_at_hire
        current_age = current_year - birth_year
        if current_age < 30:
            birth_year = current_year - random.randint(30, 35)
        elif current_age > 45:
            birth_year = current_year - random.randint(40, 45)
    else:
        age = random.randint(30, 45)
        birth_year = current_year - age
    
    return f"{birth_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"


def generate_hire_date() -> str:
    """Generate realistic hire date (1-15 years ago, in August)."""
    current_year = datetime.now().year
    years = random.randint(1, 15)
    hire_year = current_year - years
    return f"{hire_year}-08-{random.randint(15, 30):02d}"


def add_teachers_from_names(
    names: List[str],
    school: Dict,
    district_config: Dict
) -> List[Dict]:
    """
    Convert a list of names to teacher records.
    
    Args:
        names: List of full names like ["John Smith", "Jane Doe"]
        school: School info dict
        district_config: District configuration
    """
    teachers = []
    
    for full_name in names:
        parts = full_name.strip().split()
        if len(parts) < 2:
            continue
        
        # Handle titles
        if parts[0] in ["Mr.", "Ms.", "Mrs.", "Dr.", "Miss"]:
            parts = parts[1:]
        if len(parts) < 2:
            continue
        
        first_name = parts[0]
        last_name = " ".join(parts[1:])
        
        hire_date = generate_hire_date()
        hire_year = int(hire_date.split("-")[0])
        
        teacher = {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name} {last_name}",
            "email": generate_email(
                first_name, 
                last_name, 
                district_config["email_pattern"],
                district_config["domain"]
            ),
            "birth_date": generate_birth_date(hire_year),
            "school_name": school["name"],
            "school_id": school["id"],
            "position": "Teacher",
            "hire_date": hire_date,
            "school_city": school["city"],
            "school_state": district_config["state"],
            "email_generated": True,  # Flag to indicate email was generated
        }
        teachers.append(teacher)
    
    return teachers


def list_districts():
    """List all supported districts."""
    print("\n=== SUPPORTED DISTRICTS ===\n")
    for key, config in DISTRICTS.items():
        print(f"[{key}]")
        print(f"  Name: {config['name']}")
        print(f"  Domain: {config['domain']}")
        print(f"  Email Pattern: {config['email_pattern']}")
        print(f"  Schools: {len(config['schools'])}")
        print()


def add_sample_teachers(district_key: str, num_schools: int = 3):
    """
    Add sample teachers for testing.
    In production, this would be replaced with actual scraped data.
    """
    if district_key not in DISTRICTS:
        logger.error(f"Unknown district: {district_key}")
        return
    
    config = DISTRICTS[district_key]
    existing = load_existing_teachers()
    existing_emails = {t['email'].lower() for t in existing}
    
    # Sample teacher names for demonstration
    sample_names = [
        "Michael Johnson", "Sarah Williams", "Robert Brown",
        "Jennifer Davis", "William Miller", "Elizabeth Wilson",
        "David Moore", "Patricia Taylor", "Richard Anderson",
        "Linda Thomas", "Joseph Jackson", "Barbara White",
        "Charles Harris", "Margaret Martin", "Christopher Thompson",
        "Susan Garcia", "Daniel Martinez", "Nancy Robinson",
        "Matthew Clark", "Lisa Rodriguez", "Anthony Lewis",
    ]
    
    new_teachers = []
    schools_to_process = config["schools"][:num_schools]
    
    for school in schools_to_process:
        # Get 10 random names for each school
        names = random.sample(sample_names, min(10, len(sample_names)))
        teachers = add_teachers_from_names(names, school, config)
        
        for t in teachers:
            if t['email'].lower() not in existing_emails:
                new_teachers.append(t)
                existing_emails.add(t['email'].lower())
        
        logger.info(f"Processed: {school['name']} - {len(teachers)} teachers")
    
    if new_teachers:
        all_teachers = existing + new_teachers
        save_teachers(all_teachers)
        logger.info(f"Added {len(new_teachers)} new teachers from {district_key}")
    else:
        logger.info("No new teachers added (all duplicates)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Large District Teacher Scraper")
    parser.add_argument("--district", type=str, help="District key (miami-dade, lausd, nyc-doe)")
    parser.add_argument("--schools", type=int, default=3, help="Number of schools to process")
    parser.add_argument("--list", action="store_true", help="List supported districts")
    
    args = parser.parse_args()
    
    if args.list:
        list_districts()
    elif args.district:
        add_sample_teachers(args.district, args.schools)
    else:
        print("Usage:")
        print("  python district_scraper.py --list")
        print("  python district_scraper.py --district miami-dade --schools 5")
        print("\nNote: This script uses sample names for demonstration.")
        print("For real data, use browser scraping or integrate with actual staff directories.")
