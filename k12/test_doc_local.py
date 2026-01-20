"""Test K12 Document Generation (Synchronized)

Generates all document types with SYNCHRONIZED data:
- All documents share the SAME Employee ID
- All documents share the SAME School Name
- All documents share the SAME Department/Position

Usage:
    python test_doc_local.py
"""
from pathlib import Path

# Import document generators and teacher database
from img_generator import create_synced_documents, generate_blank_image
from name_generator import generate_teacher_info

def main():
    print("=" * 60)
    print("K12 Document Generation Test (SYNCHRONIZED)")
    print("=" * 60)
    
    # Get teacher info from database
    print("\n1. Getting teacher info from database...")
    teacher = generate_teacher_info()
    
    first_name = teacher["first_name"]
    last_name = teacher["last_name"]
    school_name = teacher.get("school_name", "Springfield High School")
    
    print(f"   Teacher: {first_name} {last_name}")
    print(f"   School: {school_name}")
    
    # Create output directory
    output_dir = Path(__file__).parent / "test_output"
    output_dir.mkdir(exist_ok=True)
    
    # Generate ALL documents with SYNCHRONIZED data
    print("\n2. Generating synchronized documents...")
    print("   (All documents will have SAME Employee ID and School)")
    
    result = create_synced_documents(first_name, last_name, school_name)
    
    # Print shared data
    shared = result["shared_data"]
    print(f"\n   Shared Employee ID: {shared['employee_id_formatted']}")
    print(f"   Shared School: {shared['school_name']}")
    print(f"   Shared District: {shared['district_name']}")
    
    # Save documents
    doc_names = {
        "id_card": ("ID Card (Faculty ID)", "teacher_id_card.png"),
        "hr_system": ("HR System (Employee Access)", "teacher_hr_system.png"),
        "payslip": ("Payslip (NYCAPS ESS)", "teacher_payslip.png"),
    }
    
    for doc_type, (description, filename) in doc_names.items():
        print(f"\n{'='*40}")
        print(f"Saving: {description}")
        print(f"{'='*40}")
        
        png_data = result["documents"][doc_type]
        png_path = output_dir / filename
        with open(png_path, "wb") as f:
            f.write(png_data)
        print(f"   ✓ Saved: {png_path}")
        print(f"   Size: {len(png_data)} bytes ({len(png_data)/1024:.2f} KB)")
    
    # Generate blank image separately (no sync needed)
    print(f"\n{'='*40}")
    print("Generating: Blank (White Image)")
    print(f"{'='*40}")
    
    try:
        blank_data = generate_blank_image()
        blank_path = output_dir / "teacher_blank.png"
        with open(blank_path, "wb") as f:
            f.write(blank_data)
        print(f"   ✓ Saved: {blank_path}")
        print(f"   Size: {len(blank_data)} bytes ({len(blank_data)/1024:.2f} KB)")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ All documents generated with SYNCHRONIZED data!")
    print(f"   Employee ID: {shared['employee_id_formatted']} (same in all docs)")
    print(f"   School: {shared['school_name']} (same in all docs)")
    print(f"Output directory: {output_dir}")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
