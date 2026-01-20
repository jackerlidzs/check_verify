"""K12 Teacher Info Generator - Priority School Systems

Loads REAL teacher profiles from 3 priority school systems:
- NYC DOE (New York City Department of Education) - 117 teachers
- Miami-Dade County Public Schools - 84 teachers  
- Springfield High School System (IL, MO, MA) - 50 teachers

These schools match the document templates available for verification.
"""
import json
import random
from pathlib import Path
from typing import Dict, Optional, List

# Path to teacher databases
DATA_DIR = Path(__file__).parent / "data"
PRIORITY_TEACHERS_FILE = DATA_DIR / "k12_teacher_info.json"  # Priority districts
ALL_TEACHERS_FILE = DATA_DIR / "real_teachers.json"  # All teachers

# Cache for loaded profiles
_priority_profiles = None
_all_profiles = None
_profiles_by_district = None

# Track used teachers (by email) to avoid repeats
_used_teachers = set()
USED_TEACHERS_FILE = DATA_DIR / "used_teachers.json"

def load_used_teachers() -> set:
    """Load set of used teacher emails."""
    global _used_teachers
    if USED_TEACHERS_FILE.exists():
        import json
        _used_teachers = set(json.loads(USED_TEACHERS_FILE.read_text()))
    return _used_teachers

def mark_teacher_used(email: str):
    """Mark a teacher as used."""
    import json
    _used_teachers.add(email.lower())
    USED_TEACHERS_FILE.write_text(json.dumps(list(_used_teachers)))

def reset_used_teachers():
    """Reset all used teachers."""
    global _used_teachers
    _used_teachers = set()
    if USED_TEACHERS_FILE.exists():
        USED_TEACHERS_FILE.unlink()

# Priority districts matching document templates
# Rank: 1 = highest priority (most likely to pass SheerID verification)
PRIORITY_DISTRICTS = {
    "nyc_doe": {
        "name": "NYC DOE",
        "email_domain": "schools.nyc.gov",
        "states": ["NY"],
        "template_dir": "nyc_doe",
        "rank": 1  # Highest - largest school system, well-known
    },
    "miami_dade": {
        "name": "Miami-Dade County",
        "email_domain": "dadeschools.net", 
        "states": ["FL"],
        "template_dir": "miami_dade",
        "rank": 2  # Second - major school system
    },
    "springfield_high": {
        "name": "Springfield High",
        "email_domains": ["springfield.k12.il.us", "sps186.org", "sps.org", "springfieldpublicschools.com"],
        "states": ["IL", "MO", "MA"],
        "template_dir": "springfield_high",
        "rank": 3  # Third
    }
}

# Districts in priority order (highest rank first)
DISTRICT_PRIORITY_ORDER = ["nyc_doe", "miami_dade", "springfield_high"]

# Priority email domains (high chance of instant verification)
PRIORITY_EMAIL_DOMAINS = [
    "@schools.nyc.gov",      # NYC DOE - Rank 1
    "@dadeschools.net",      # Miami-Dade - Rank 2
    "@sps186.org",           # Springfield IL
    "@springfield.k12.il.us",
    "@troy.k12.mi.us",       # Troy School District
]

def score_teacher_quality(teacher: Dict) -> int:
    """Score teacher profile quality for SheerID verification.
    
    Higher score = more likely to pass instant verification.
    
    Scoring:
    - Priority email domain: +50
    - Position contains 'Teacher': +30
    - Has school name: +10
    - Has employee_id: +5
    - Has hire_date: +5
    
    Returns:
        Quality score (0-100)
    """
    score = 0
    email = teacher.get('email', '').lower()
    position = teacher.get('position', '').lower()
    
    # Priority email domain (+50)
    for domain in PRIORITY_EMAIL_DOMAINS:
        if domain.lower() in email:
            score += 50
            break
    
    # Position is Teacher (+30)
    if 'teacher' in position:
        score += 30
    elif 'staff' in position or 'educator' in position:
        score += 15
    
    # Has complete info
    if teacher.get('school_name'):
        score += 10
    if teacher.get('employee_id'):
        score += 5
    if teacher.get('hire_date'):
        score += 5
    
    return score


def get_high_quality_teachers(teachers: List[Dict], min_score: int = 50) -> List[Dict]:
    """Filter teachers by quality score.
    
    Args:
        teachers: List of teacher profiles
        min_score: Minimum quality score required
        
    Returns:
        List of high-quality teachers, sorted by score descending
    """
    scored = [(t, score_teacher_quality(t)) for t in teachers]
    qualified = [(t, s) for t, s in scored if s >= min_score]
    qualified.sort(key=lambda x: x[1], reverse=True)
    return [t for t, s in qualified]

def load_priority_profiles() -> Dict:
    """Load teacher profiles from 3 priority school systems."""
    global _priority_profiles, _profiles_by_district
    
    if _priority_profiles is not None:
        return _priority_profiles, _profiles_by_district
    
    if not PRIORITY_TEACHERS_FILE.exists():
        # Fallback: try to load from all teachers and filter
        return _load_and_filter_priority()
    
    with open(PRIORITY_TEACHERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # data format: {"nyc_doe": [...], "miami_dade": [...], "springfield_high": [...]}
    _profiles_by_district = data
    
    # Flatten all priority profiles
    all_priority = []
    for district, teachers in data.items():
        all_priority.extend(teachers)
    
    _priority_profiles = all_priority
    
    return all_priority, data


def _load_and_filter_priority() -> tuple:
    """Fallback: Load from real_teachers.json and filter for priority districts."""
    global _priority_profiles, _profiles_by_district
    
    if not ALL_TEACHERS_FILE.exists():
        raise FileNotFoundError(
            f"Teacher database not found: {ALL_TEACHERS_FILE}\n"
            "Please run scraping to populate real_teachers.json"
        )
    
    with open(ALL_TEACHERS_FILE, "r", encoding="utf-8") as f:
        all_data = json.load(f)
    
    priority = {
        "nyc_doe": [],
        "miami_dade": [],
        "springfield_high": []
    }
    
    for teacher in all_data:
        email = teacher.get("email", "").lower()
        state = teacher.get("school_state", "")
        school = teacher.get("school_name", "").lower()
        
        # NYC DOE
        if "@schools.nyc.gov" in email:
            priority["nyc_doe"].append(teacher)
        # Miami-Dade
        elif "@dadeschools.net" in email:
            priority["miami_dade"].append(teacher)
        # Springfield
        elif any(d in email for d in ["springfield", "sps186", "sps.org"]):
            priority["springfield_high"].append(teacher)
        elif "springfield" in school or "lanphier" in school or "kickapoo" in school:
            priority["springfield_high"].append(teacher)
    
    _profiles_by_district = priority
    
    all_priority = []
    for teachers in priority.values():
        all_priority.extend(teachers)
    
    _priority_profiles = all_priority
    
    return all_priority, priority


def get_teacher_for_district(district: str = None) -> Optional[Dict]:
    """Get a random unused teacher from a specific priority district.
    
    Prioritizes high-quality teachers (score >= 50) first.
    Filters out already-used teachers.
    
    Args:
        district: One of 'nyc_doe', 'miami_dade', 'springfield_high'
                  If None, picks from any priority district
    """
    # Load used teachers
    load_used_teachers()
    
    _, profiles_by_district = load_priority_profiles()
    
    def filter_unused(teachers: List[Dict]) -> List[Dict]:
        """Filter out used teachers."""
        return [t for t in teachers if t.get('email', '').lower() not in _used_teachers]
    
    if district and district in profiles_by_district:
        teachers = profiles_by_district[district]
        if teachers:
            # Filter unused first
            unused = filter_unused(teachers)
            if not unused:
                # All used - reset and try again
                reset_used_teachers()
                unused = teachers
            
            # Try high-quality unused teachers first
            high_quality = get_high_quality_teachers(unused, min_score=50)
            if high_quality:
                return random.choice(high_quality)
            return random.choice(unused)
    
    # Pick from any priority district - prioritize high quality + unused
    all_priority, _ = load_priority_profiles()
    if all_priority:
        unused = filter_unused(all_priority)
        if not unused:
            reset_used_teachers()
            unused = all_priority
            
        high_quality = get_high_quality_teachers(unused, min_score=50)
        if high_quality:
            return random.choice(high_quality)
        return random.choice(unused)
    
    return None


def get_random_teacher_profile(school_id: str = None, district: str = None) -> Optional[Dict]:
    """Get a random REAL teacher profile.
    
    Args:
        school_id: Optional school ID to filter by
        district: Optional district to filter by (nyc_doe, miami_dade, springfield_high)
    
    Returns:
        Teacher profile dict or None
    """
    # Prioritize district-based lookup
    if district:
        return get_teacher_for_district(district)
    
    all_profiles, profiles_by_district = load_priority_profiles()
    
    # If specific school requested, filter
    if school_id:
        matching = [p for p in all_profiles if p.get("school_id") == school_id]
        if matching:
            return random.choice(matching)
    
    # Otherwise pick from all priority profiles
    return random.choice(all_profiles) if all_profiles else None


def generate_teacher_info(school_id: str = None, district: str = None) -> Dict:
    """Generate teacher info from priority school systems.
    
    Args:
        school_id: Optional specific school ID
        district: Optional specific district (nyc_doe, miami_dade, springfield_high)
        
    Returns:
        Dict with complete teacher information including employee_id, salary, department
        
    Raises:
        FileNotFoundError: If teacher database doesn't exist
        ValueError: If no valid profiles found
    """
    profile = get_random_teacher_profile(school_id, district)
    
    if not profile:
        raise ValueError("No valid teacher profiles found")
    
    # Return ALL fields from enriched database
    return {
        # Basic info
        "first_name": profile["first_name"],
        "last_name": profile["last_name"],
        "full_name": profile["full_name"],
        "email": profile["email"],
        "birth_date": profile.get("birth_date", "1985-01-15"),
        
        # School info
        "school_id": profile.get("school_id"),
        "school_name": profile.get("school_name"),
        "school_city": profile.get("school_city"),
        "school_state": profile.get("school_state"),
        
        # Position & Employment
        "position": profile.get("position", "Teacher"),
        "hire_date": profile.get("hire_date"),
        "department": profile.get("department", "General Education"),
        
        # Enriched fields for document consistency
        "employee_id": profile.get("employee_id"),
        "employee_id_formatted": profile.get("employee_id_formatted"),
        "salary_step": profile.get("salary_step"),
        "annual_salary": profile.get("annual_salary"),
        "pension_number": profile.get("pension_number"),
    }


def get_district_for_template(template_dir: str) -> str:
    """Get district name based on template directory.
    
    Args:
        template_dir: Directory name like 'nyc_doe', 'miami_dade', 'springfield_high'
    
    Returns:
        District identifier
    """
    for district, info in PRIORITY_DISTRICTS.items():
        if info.get("template_dir") == template_dir:
            return district
    return None


def get_database_stats() -> Dict:
    """Get statistics about the priority teacher database."""
    all_profiles, profiles_by_district = load_priority_profiles()
    
    # Count by school
    schools = {}
    for profile in all_profiles:
        school = profile.get("school_name", "Unknown")
        schools[school] = schools.get(school, 0) + 1
    
    # Count by district
    district_counts = {d: len(teachers) for d, teachers in profiles_by_district.items()}
    
    return {
        "total_teachers": len(all_profiles),
        "districts": district_counts,
        "schools": schools,
        "priority_districts": list(PRIORITY_DISTRICTS.keys()),
    }


# Legacy compatibility functions
class NameGenerator:
    """Legacy name generator class for compatibility."""
    
    @classmethod
    def generate(cls) -> Dict:
        """Generate random name (legacy compatibility)."""
        teacher = generate_teacher_info()
        return {
            "first_name": teacher["first_name"],
            "last_name": teacher["last_name"],
            "full_name": teacher["full_name"]
        }


def generate_email() -> str:
    """Generate email (legacy compatibility)."""
    teacher = generate_teacher_info()
    return teacher["email"]


def generate_birth_date() -> str:
    """Generate birth date (legacy compatibility)."""
    teacher = generate_teacher_info()
    return teacher["birth_date"]


if __name__ == "__main__":
    print("K12 Priority School Systems Database")
    print("=" * 50)
    
    try:
        stats = get_database_stats()
        print(f"\nTotal REAL teachers: {stats['total_teachers']}")
        
        print(f"\nPriority Districts:")
        for district, count in stats['districts'].items():
            print(f"  - {district}: {count} teachers")
        
        print(f"\nSchools:")
        for school, count in sorted(stats['schools'].items()):
            print(f"  - {school}: {count}")
        
        print(f"\nSample teachers from each district:")
        for district in ["nyc_doe", "miami_dade", "springfield_high"]:
            print(f"\n  [{district.upper()}]")
            teacher = generate_teacher_info(district=district)
            print(f"    {teacher['full_name']} - {teacher['position']}")
            print(f"    Email: {teacher['email']}")
            print(f"    School: {teacher['school_name']}, {teacher['school_state']}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
