"""
Script to migrate teacher data from JSON to SQLite database.
Run: python -m app.db.migrate
"""
import json
from pathlib import Path
from sqlalchemy.orm import Session

from .database import SessionLocal, init_db
from .models import Teacher
from . import crud


def migrate_json_to_sqlite():
    """Load teachers from JSON and insert into SQLite."""
    # Path to original JSON file
    json_path = Path(__file__).parent.parent.parent.parent / "k12" / "data" / "k12_teacher_info.json"
    
    if not json_path.exists():
        print(f"❌ JSON file not found: {json_path}")
        return
    
    # Load JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Initialize database
    init_db()
    
    db = SessionLocal()
    
    try:
        total = 0
        
        for district, teachers in data.items():
            print(f"📂 Processing district: {district}")
            
            for teacher_data in teachers:
                # Check if exists
                existing = db.query(Teacher).filter(
                    Teacher.email == teacher_data.get("email")
                ).first()
                
                if existing:
                    continue
                
                # Create teacher
                teacher = Teacher(
                    first_name=teacher_data.get("first_name", ""),
                    last_name=teacher_data.get("last_name", ""),
                    email=teacher_data.get("email"),
                    school_name=teacher_data.get("school_name") or teacher_data.get("school"),
                    district=district,
                    employee_id=teacher_data.get("employee_id"),
                    position=teacher_data.get("position"),
                    department=teacher_data.get("department"),
                    annual_salary=teacher_data.get("annual_salary"),
                    hire_date=teacher_data.get("hire_date")
                )
                
                db.add(teacher)
                total += 1
        
        db.commit()
        print(f"✅ Migrated {total} teachers to SQLite")
        
        # Show stats
        for district in data.keys():
            count = db.query(Teacher).filter(Teacher.district == district).count()
            print(f"   {district}: {count} teachers")
            
    finally:
        db.close()


if __name__ == "__main__":
    migrate_json_to_sqlite()
