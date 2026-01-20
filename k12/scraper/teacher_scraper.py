"""
K12 Teacher Scraper
Scrape teacher information from school staff directories.

Usage:
    python teacher_scraper.py --phase 1  # Run phase 1 (schools 1-5)
    python teacher_scraper.py --phase 2  # Run phase 2 (schools 6-10)
    python teacher_scraper.py --list     # List all schools
"""

import json
import random
import argparse
import logging
import httpx
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re
import time

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
SCHOOLS_FILE = DATA_DIR / "k12_schools.json"
TEACHERS_FILE = DATA_DIR / "real_teachers.json"

# Config
SCHOOLS_PER_PHASE = 5
TEACHERS_PER_SCHOOL = 10


def load_schools() -> List[Dict]:
    """Load K12 schools from JSON file."""
    with open(SCHOOLS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


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


def generate_birth_date(hire_year: int = None) -> str:
    """
    Generate a realistic birth date for a teacher.
    
    If hire_year is provided, estimate based on seniority.
    Target age range: 30-45 years old.
    """
    current_year = datetime.now().year
    
    if hire_year:
        # Estimate: teacher was 25-35 when hired
        age_at_hire = random.randint(25, 35)
        birth_year = hire_year - age_at_hire
        
        # Ensure current age is 30-45
        current_age = current_year - birth_year
        if current_age < 30:
            birth_year = current_year - random.randint(30, 35)
        elif current_age > 45:
            birth_year = current_year - random.randint(40, 45)
    else:
        # No hire year: random age 30-45
        age = random.randint(30, 45)
        birth_year = current_year - age
    
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)  # Safe for all months
    
    return f"{birth_year}-{birth_month:02d}-{birth_day:02d}"


def generate_hire_date() -> str:
    """Generate a realistic hire date (1-15 years ago, in August)."""
    today = datetime.now()
    years_employed = random.randint(1, 15)
    hire_year = today.year - years_employed
    # Most teachers are hired in August (start of school year)
    hire_month = 8
    hire_day = random.randint(15, 30)
    
    return f"{hire_year}-{hire_month:02d}-{hire_day:02d}"


def extract_email_from_text(text: str) -> Optional[str]:
    """Extract email address from text."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0) if match else None


def parse_name(full_name: str) -> tuple:
    """Parse full name into first and last name."""
    parts = full_name.strip().split()
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = ' '.join(parts[1:])
    elif len(parts) == 1:
        first_name = parts[0]
        last_name = "Teacher"
    else:
        first_name = "Unknown"
        last_name = "Teacher"
    
    # Clean up prefixes/suffixes
    first_name = first_name.replace("Dr.", "").replace("Mr.", "").replace("Mrs.", "").replace("Ms.", "").strip()
    
    return first_name, last_name


def scrape_staff_page(url: str, school: Dict, max_teachers: int = 10) -> List[Dict]:
    """Scrape teacher info from a staff directory page."""
    teachers = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = httpx.get(url, headers=headers, timeout=30.0, follow_redirects=True)
        
        if response.status_code != 200:
            logger.warning(f"Failed to fetch {url}: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Common selectors for staff directories
        # Try multiple patterns
        staff_elements = []
        
        # Pattern 1: Cards with name and email
        for card in soup.select('.staff-card, .faculty-card, .team-member, .person-card'):
            name_elem = card.select_one('h2, h3, h4, .name, .title')
            email_elem = card.select_one('a[href^="mailto:"]')
            position_elem = card.select_one('.position, .role, .job-title, .department')
            
            if name_elem and email_elem:
                staff_elements.append({
                    'name': name_elem.get_text(strip=True),
                    'email': email_elem.get('href', '').replace('mailto:', ''),
                    'position': position_elem.get_text(strip=True) if position_elem else 'Teacher'
                })
        
        # Pattern 2: Table rows
        for row in soup.select('table tr'):
            cells = row.select('td')
            if len(cells) >= 2:
                name = cells[0].get_text(strip=True)
                email_link = row.select_one('a[href^="mailto:"]')
                if email_link and name:
                    staff_elements.append({
                        'name': name,
                        'email': email_link.get('href', '').replace('mailto:', ''),
                        'position': cells[1].get_text(strip=True) if len(cells) > 1 else 'Teacher'
                    })
        
        # Pattern 3: Links with mailto
        if not staff_elements:
            for link in soup.select('a[href^="mailto:"]'):
                email = link.get('href', '').replace('mailto:', '')
                # Try to find associated name
                parent = link.parent
                if parent:
                    name_text = parent.get_text(strip=True)
                    # Extract name before email
                    name = name_text.split(email)[0].strip() if email in name_text else name_text
                    if name and '@' not in name:
                        staff_elements.append({
                            'name': name[:50],  # Limit length
                            'email': email,
                            'position': 'Teacher'
                        })
        
        # Convert to teacher format
        seen_emails = set()
        for elem in staff_elements[:max_teachers]:
            email = elem['email'].lower().strip()
            
            # Skip duplicates and invalid
            if not email or '@' not in email or email in seen_emails:
                continue
            seen_emails.add(email)
            
            first_name, last_name = parse_name(elem['name'])
            
            teacher = {
                "first_name": first_name,
                "last_name": last_name,
                "full_name": f"{first_name} {last_name}",
                "email": email,
                "birth_date": generate_birth_date(),
                "school_name": school['name'],
                "school_id": str(school['id']),
                "position": elem.get('position', 'Teacher'),
                "hire_date": generate_hire_date(),
                "school_city": school.get('city', ''),
                "school_state": school.get('state', '')
            }
            teachers.append(teacher)
        
        logger.info(f"Found {len(teachers)} teachers from {school['name']}")
        
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
    
    return teachers


# Known school staff directory URLs
SCHOOL_STAFF_URLS = {
    # Format: school_id -> staff_directory_url
    "237830": "https://www.kinkaid.org/about/faculty-and-staff",  # The Kinkaid School
    "3545593": "https://www.spenceschool.org/about/faculty-staff",  # The Spence School
    "253545": "https://www.archer.org/about/faculty",  # Archer School For Girls
    "186974": "https://www.academyatthelakes.org/about/faculty-staff",  # Academy At The Lakes
}


def get_school_staff_url(school: Dict) -> Optional[str]:
    """Get staff directory URL for a school."""
    school_id = str(school['id'])
    
    # Check known URLs first
    if school_id in SCHOOL_STAFF_URLS:
        return SCHOOL_STAFF_URLS[school_id]
    
    # Try to construct URLs for public schools (k12.*.us domains)
    school_name = school['name'].lower()
    state = school.get('state', '').lower()
    
    # Common public school patterns
    # These would need manual verification
    return None


def run_phase(phase_number: int):
    """Run a single scraping phase (5 schools)."""
    schools = load_schools()
    existing_teachers = load_existing_teachers()
    existing_emails = {t['email'].lower() for t in existing_teachers}
    
    # Calculate range for this phase
    start_idx = (phase_number - 1) * SCHOOLS_PER_PHASE
    end_idx = start_idx + SCHOOLS_PER_PHASE
    
    phase_schools = schools[start_idx:end_idx]
    
    if not phase_schools:
        logger.warning(f"No schools found for phase {phase_number}")
        return
    
    logger.info(f"=== PHASE {phase_number}: Schools {start_idx+1}-{end_idx} ===")
    
    new_teachers = []
    
    for school in phase_schools:
        school_id = str(school['id'])
        school_name = school['name']
        
        url = get_school_staff_url(school)
        
        if not url:
            logger.info(f"Skipping {school_name} (no known staff URL)")
            continue
        
        logger.info(f"Scraping: {school_name}")
        
        teachers = scrape_staff_page(url, school, TEACHERS_PER_SCHOOL)
        
        # Filter out existing emails
        for teacher in teachers:
            if teacher['email'].lower() not in existing_emails:
                new_teachers.append(teacher)
                existing_emails.add(teacher['email'].lower())
        
        # Be nice to servers
        time.sleep(2)
    
    if new_teachers:
        # Append to existing
        all_teachers = existing_teachers + new_teachers
        save_teachers(all_teachers)
        logger.info(f"Added {len(new_teachers)} new teachers")
    else:
        logger.info("No new teachers found in this phase")


def list_schools():
    """List all schools with known staff URLs."""
    schools = load_schools()
    
    print("\n=== Schools with Known Staff URLs ===\n")
    for school in schools[:20]:  # Show first 20
        school_id = str(school['id'])
        has_url = "[Y]" if school_id in SCHOOL_STAFF_URLS else "[N]"
        print(f"{has_url} [{school_id}] {school['name']} ({school['city']}, {school['state']})")
    
    print(f"\nTotal schools: {len(schools)}")
    print(f"Schools with URLs: {len(SCHOOL_STAFF_URLS)}")


def add_manual_teachers():
    """Add teachers manually (for schools without scrapable directories)."""
    # This is a helper function to add verified teacher data manually
    
    manual_teachers = [
        # Example format - these would be real verified teachers
        # {
        #     "first_name": "John",
        #     "last_name": "Doe",
        #     "full_name": "John Doe",
        #     "email": "jdoe@school.k12.tx.us",
        #     "birth_date": "1985-03-15",
        #     "school_name": "Example High School",
        #     "school_id": "123456",
        #     "position": "Math Teacher",
        #     "hire_date": "2018-08-15",
        #     "school_city": "Houston",
        #     "school_state": "TX"
        # }
    ]
    
    if manual_teachers:
        existing = load_existing_teachers()
        existing_emails = {t['email'].lower() for t in existing}
        
        new_count = 0
        for teacher in manual_teachers:
            if teacher['email'].lower() not in existing_emails:
                existing.append(teacher)
                new_count += 1
        
        if new_count > 0:
            save_teachers(existing)
            logger.info(f"Added {new_count} manual teachers")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="K12 Teacher Scraper")
    parser.add_argument("--phase", type=int, help="Phase number to run (1, 2, 3...)")
    parser.add_argument("--list", action="store_true", help="List schools")
    parser.add_argument("--manual", action="store_true", help="Add manual teachers")
    
    args = parser.parse_args()
    
    if args.list:
        list_schools()
    elif args.manual:
        add_manual_teachers()
    elif args.phase:
        run_phase(args.phase)
    else:
        print("Usage:")
        print("  python teacher_scraper.py --phase 1  # Run phase 1")
        print("  python teacher_scraper.py --list     # List schools")
        print("  python teacher_scraper.py --manual   # Add manual teachers")
