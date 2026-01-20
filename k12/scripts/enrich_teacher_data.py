"""Enrich teacher data with employee_id, salary, department

This script adds missing fields to k12_teacher_info.json to ensure
document generation is consistent with teacher data for SheerID verification.
"""
import json
import hashlib
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
K12_TEACHERS_FILE = DATA_DIR / "k12_teacher_info.json"
OUTPUT_FILE = DATA_DIR / "k12_teacher_info_enriched.json"

# Salary ranges by experience level (based on position keywords)
SALARY_TIERS = {
    "new": {
        "steps": ["Step 1, BA", "Step 2, BA", "Step 3, BA+15"],
        "range": (45000, 55000),
        "keywords": ["new", "first year", "entry"]
    },
    "mid": {
        "steps": ["Step 4, BA+30", "Step 5, BA+30", "Step 6, MA"],
        "range": (55000, 72000),
        "keywords": ["teacher", "faculty", "specialist"]
    },
    "senior": {
        "steps": ["Step 7, MA+15", "Step 8, MA+30", "Step 9, MA+45", "Step 10, Doctorate"],
        "range": (72000, 95000),
        "keywords": ["chair", "coordinator", "lead", "coach", "principal", "director"]
    }
}

# Department mappings
DEPARTMENT_MAP = {
    "math": "Mathematics Department",
    "mathematics": "Mathematics Department",
    "english": "English Department",
    "language arts": "English Department",
    "science": "Science Department",
    "biology": "Science Department",
    "chemistry": "Science Department",
    "physics": "Science Department",
    "history": "Social Studies Department",
    "social studies": "Social Studies Department",
    "geography": "Social Studies Department",
    "economics": "Social Studies Department",
    "physical education": "Physical Education Department",
    "pe": "Physical Education Department",
    "art": "Art Department",
    "music": "Music Department",
    "drama": "Art Department",
    "theater": "Art Department",
    "spanish": "World Languages Department",
    "french": "World Languages Department",
    "german": "World Languages Department",
    "chinese": "World Languages Department",
    "computer": "Technology Department",
    "technology": "Technology Department",
    "engineering": "Technology Department",
    "robotics": "Technology Department",
    "special education": "Special Education Department",
    "sped": "Special Education Department",
    "esl": "ESL Department",
    "esol": "ESL Department",
    "psychology": "Counseling Department",
    "counselor": "Counseling Department",
    "health": "Health & Physical Education",
    "journalism": "English Department",
}


def generate_stable_employee_id(teacher: dict) -> str:
    """Generate a stable employee ID based on teacher's unique info.
    
    Uses hash of email + school to ensure same teacher always gets same ID.
    """
    unique_str = f"{teacher['email']}_{teacher['school_name']}"
    hash_val = int(hashlib.md5(unique_str.encode()).hexdigest()[:7], 16)
    # 7-digit employee ID
    employee_id = str((hash_val % 9000000) + 1000000)
    return employee_id


def get_salary_tier(position: str) -> str:
    """Determine salary tier based on position keywords."""
    position_lower = position.lower()
    
    # Check senior keywords first
    for keyword in SALARY_TIERS["senior"]["keywords"]:
        if keyword in position_lower:
            return "senior"
    
    # Default to mid-level for regular teachers
    return "mid"


def generate_salary(position: str, hire_date: str = None) -> tuple:
    """Generate realistic salary based on position and seniority."""
    tier = get_salary_tier(position)
    tier_info = SALARY_TIERS[tier]
    
    # Pick salary step and amount
    step = random.choice(tier_info["steps"])
    salary = random.randint(tier_info["range"][0], tier_info["range"][1])
    
    # Round to nearest 500
    salary = round(salary / 500) * 500
    
    return step, salary


def extract_department(position: str) -> str:
    """Extract department from position title."""
    position_lower = position.lower()
    
    for keyword, department in DEPARTMENT_MAP.items():
        if keyword in position_lower:
            return department
    
    # Default department for unknown positions
    return "General Education"


def generate_pension_number(employee_id: str) -> str:
    """Generate pension number from employee ID."""
    return f"TRS-{employee_id}"


def enrich_teacher(teacher: dict) -> dict:
    """Add all missing fields to teacher data."""
    enriched = teacher.copy()
    
    # 1. Employee ID (stable, based on hash)
    if not enriched.get("employee_id"):
        enriched["employee_id"] = generate_stable_employee_id(teacher)
    
    # 2. Salary
    if not enriched.get("annual_salary"):
        step, salary = generate_salary(
            teacher.get("position", "Teacher"),
            teacher.get("hire_date")
        )
        enriched["salary_step"] = step
        enriched["annual_salary"] = salary
    
    # 3. Department
    if not enriched.get("department"):
        enriched["department"] = extract_department(teacher.get("position", "Teacher"))
    
    # 4. Pension number
    if not enriched.get("pension_number"):
        enriched["pension_number"] = generate_pension_number(enriched["employee_id"])
    
    # 5. Employee ID formatted
    enriched["employee_id_formatted"] = f"E-{enriched['employee_id']}"
    
    return enriched


def enrich_all_teachers():
    """Enrich all teachers in k12_teacher_info.json"""
    
    # Load existing data
    with open(K12_TEACHERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Data is structured as: {"nyc_doe": [...], "miami_dade": [...], "springfield_high": [...]}
    enriched_data = {}
    stats = {"total": 0, "enriched": 0}
    
    for district, teachers in data.items():
        print(f"\n{'='*50}")
        print(f"Processing {district.upper()}: {len(teachers)} teachers")
        print("="*50)
        
        enriched_teachers = []
        for teacher in teachers:
            enriched = enrich_teacher(teacher)
            enriched_teachers.append(enriched)
            stats["total"] += 1
            
            # Show first 3 as sample
            if len(enriched_teachers) <= 3:
                print(f"\n  {enriched['full_name']}:")
                print(f"    Employee ID: {enriched['employee_id_formatted']}")
                print(f"    Salary: ${enriched['annual_salary']:,} ({enriched['salary_step']})")
                print(f"    Department: {enriched['department']}")
        
        enriched_data[district] = enriched_teachers
        print(f"\n  [OK] Enriched {len(enriched_teachers)} teachers")
    
    # Save enriched data
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(enriched_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*50}")
    print(f"DONE! Saved to: {OUTPUT_FILE}")
    print(f"Total teachers enriched: {stats['total']}")
    print("="*50)
    
    return enriched_data


if __name__ == "__main__":
    enrich_all_teachers()
