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
PRIORITY_TEACHERS_FILE = DATA_DIR / "k12_teacher_info_enriched.json"  # Priority districts with SheerID IDs
ALL_TEACHERS_FILE = DATA_DIR / "real_teachers.json"  # All teachers
LEGACY_TEACHERS_FILE = DATA_DIR / "k12_teacher_info.json"  # Fallback without SheerID IDs

# Cache for loaded profiles
_priority_profiles = None
_all_profiles = None
_profiles_by_district = None

# Priority districts matching document templates
PRIORITY_DISTRICTS = {
    "nyc_doe": {
        "name": "NYC DOE",
        "email_domain": "schools.nyc.gov",
        "states": ["NY"],
        "template_dir": "nyc_doe"
    },
    "miami_dade": {
        "name": "Miami-Dade County",
        "email_domain": "dadeschools.net", 
        "states": ["FL"],
        "template_dir": "miami_dade"
    },
    "springfield_high": {
        "name": "Springfield High",
        "email_domains": ["springfield.k12.il.us", "sps186.org", "sps.org", "springfieldpublicschools.com"],
        "states": ["IL", "MO", "MA"],
        "template_dir": "springfield_high"
    }
}


def load_priority_profiles() -> Dict:
    """Load teacher profiles from 3 priority school systems."""
    global _priority_profiles, _profiles_by_district
    
    if _priority_profiles is not None:
        return _priority_profiles, _profiles_by_district
    
    # Try enriched file first, then legacy, then filter from all
    file_to_load = PRIORITY_TEACHERS_FILE
    if not file_to_load.exists():
        file_to_load = LEGACY_TEACHERS_FILE
    
    if not file_to_load.exists():
        # Fallback: try to load from all teachers and filter
        return _load_and_filter_priority()
    
    with open(file_to_load, "r", encoding="utf-8") as f:
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
    """Get a random teacher from a specific priority district.
    
    Args:
        district: One of 'nyc_doe', 'miami_dade', 'springfield_high'
                  If None, picks from any priority district
    """
    _, profiles_by_district = load_priority_profiles()
    
    if district and district in profiles_by_district:
        teachers = profiles_by_district[district]
        if teachers:
            return random.choice(teachers)
    
    # Pick from any priority district
    all_priority, _ = load_priority_profiles()
    if all_priority:
        return random.choice(all_priority)
    
    return None


def get_high_priority_teacher() -> Optional[Dict]:
    """Get a teacher with highest likelihood of instant verification.
    
    Priority order (based on SheerID data agreements):
    1. NYC DOE (@schools.nyc.gov) - Largest school district, likely in database
    2. Miami-Dade (@dadeschools.net) - Large district
    3. Springfield/Other - Smaller, may require email verification
    
    Returns:
        Teacher profile dict optimized for instant verification
    """
    _, profiles_by_district = load_priority_profiles()
    
    # Priority order for instant verification
    priority_order = ['nyc_doe', 'miami_dade', 'springfield_high']
    
    for district in priority_order:
        teachers = profiles_by_district.get(district, [])
        if teachers:
            # Get random teacher from this district
            return random.choice(teachers)
    
    # Fallback to any available
    all_profiles, _ = load_priority_profiles()
    return random.choice(all_profiles) if all_profiles else None


def get_nyc_doe_teacher() -> Optional[Dict]:
    """Get a teacher specifically from NYC DOE - highest chance of instant verify.
    
    NYC DOE has data-sharing agreements with many verification services.
    Teachers with @schools.nyc.gov email are most likely to instant-verify.
    """
    return get_teacher_for_district('nyc_doe')


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
        
        # SheerID integration (from enriched data)
        "sheerid_school_id": profile.get("sheerid_school_id"),
        "sheerid_school_name": profile.get("sheerid_school_name"),
        "sheerid_school_type": profile.get("sheerid_school_type", "HIGH_SCHOOL"),
        
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
