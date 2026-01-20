"""Test script to verify complete document-teacher data consistency

Generates documents for all 3 districts and validates that ALL fields match.
"""
import json
from pathlib import Path
from k12.name_generator import generate_teacher_info
from k12.img_generator import generate_teacher_png, TeacherDocumentData

output_dir = Path('k12/output/test_consistency')
output_dir.mkdir(parents=True, exist_ok=True)

districts = ['nyc_doe', 'miami_dade', 'springfield_high']
doc_types = ['id_card', 'payslip', 'offer_letter']

results = []
all_passed = True

for district in districts:
    print(f'\n{"="*60}')
    print(f' {district.upper()} ')
    print("="*60)
    
    # Get teacher from this district (with ALL enriched data)
    teacher = generate_teacher_info(district=district)
    
    print(f'\n[Teacher Data from JSON]')
    print(f'  Name: {teacher["full_name"]}')
    print(f'  Email: {teacher["email"]}')
    print(f'  School: {teacher["school_name"]}')
    print(f'  Position: {teacher.get("position", "N/A")}')
    print(f'  Employee ID: {teacher.get("employee_id_formatted", "N/A")}')
    print(f'  Salary: ${teacher.get("annual_salary", 0):,} ({teacher.get("salary_step", "N/A")})')
    print(f'  Department: {teacher.get("department", "N/A")}')
    print(f'  Hire Date: {teacher.get("hire_date", "N/A")}')
    
    # Create TeacherDocumentData with ALL enriched fields
    shared_data = TeacherDocumentData(
        teacher['first_name'],
        teacher['last_name'],
        school_name=teacher['school_name'],
        school_template=district,
        position=teacher.get('position'),
        hire_date=teacher.get('hire_date'),
        employee_id=teacher.get('employee_id'),
        annual_salary=teacher.get('annual_salary'),
        salary_step=teacher.get('salary_step'),
        department=teacher.get('department'),
        pension_number=teacher.get('pension_number'),
    )
    
    print(f'\n[Document Data (TeacherDocumentData)]')
    print(f'  Name: {shared_data.full_name}')
    print(f'  Employee ID: {shared_data.employee_id_formatted}')
    print(f'  Position: {shared_data.position}')
    print(f'  Salary: {shared_data.salary_formatted}')
    print(f'  Department: {shared_data.department}')
    print(f'  Hire Date: {shared_data.hire_date}')
    print(f'  District: {shared_data.district_name}')
    
    # Validate consistency
    print(f'\n[Consistency Check]')
    checks = [
        ('Full Name', teacher['full_name'], shared_data.full_name),
        ('Employee ID', teacher.get('employee_id'), str(shared_data.employee_id)),
        ('Position', teacher.get('position'), shared_data.position),
        ('Salary', teacher.get('annual_salary'), shared_data.annual_salary),
        ('Salary Step', teacher.get('salary_step'), shared_data.salary_step),
        ('Department', teacher.get('department'), shared_data.department),
        ('School', teacher.get('school_name'), shared_data.school_name),
    ]
    
    district_passed = True
    for field_name, teacher_val, doc_val in checks:
        match = str(teacher_val) == str(doc_val) if teacher_val else True
        status = '[OK]' if match else '[FAIL]'
        if not match:
            district_passed = False
            all_passed = False
        print(f'  {status} {field_name}: "{teacher_val}" == "{doc_val}"')
    
    # Generate all document types
    print(f'\n[Generating Documents]')
    district_dir = output_dir / district
    district_dir.mkdir(parents=True, exist_ok=True)
    
    for doc_type in doc_types:
        png_data = generate_teacher_png(
            teacher['first_name'],
            teacher['last_name'],
            teacher['school_name'],
            doc_type=doc_type,
            shared_data=shared_data,
            school_template=district
        )
        
        filepath = district_dir / f'{doc_type}.png'
        filepath.write_bytes(png_data)
        print(f'  Saved: {filepath.name} ({len(png_data)/1024:.1f}KB)')
    
    # Save teacher + document info
    result = {
        'district': district,
        'teacher_data': teacher,
        'document_data': {
            'full_name': shared_data.full_name,
            'employee_id': shared_data.employee_id,
            'employee_id_formatted': shared_data.employee_id_formatted,
            'position': shared_data.position,
            'department': shared_data.department,
            'annual_salary': shared_data.annual_salary,
            'salary_step': shared_data.salary_step,
            'salary_formatted': shared_data.salary_formatted,
            'school_name': shared_data.school_name,
            'district_name': shared_data.district_name,
            'hire_date': shared_data.hire_date,
        },
        'consistency_passed': district_passed,
    }
    results.append(result)

# Save all results
info_path = output_dir / 'consistency_test_results.json'
info_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))

print(f'\n{"="*60}')
print(f' SUMMARY ')
print("="*60)
print(f'\nResults saved to: {info_path}')
print(f'Documents saved to: {output_dir}')

if all_passed:
    print(f'\n[SUCCESS] All consistency checks PASSED!')
else:
    print(f'\n[WARNING] Some consistency checks FAILED - review results')
