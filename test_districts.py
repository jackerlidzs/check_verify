"""Test script to generate documents for all 3 priority districts"""
import json
from pathlib import Path
from k12.name_generator import generate_teacher_info
from k12.img_generator import generate_teacher_png, TeacherDocumentData

output_dir = Path('k12/output/test_districts')
output_dir.mkdir(parents=True, exist_ok=True)

districts = ['nyc_doe', 'miami_dade', 'springfield_high']

results = []

for district in districts:
    print(f'\n{"="*50}')
    print(f'{district.upper()}')
    print("="*50)
    
    # Get teacher from this district
    teacher = generate_teacher_info(district=district)
    print(f'Teacher: {teacher["full_name"]}')
    print(f'Email: {teacher["email"]}')
    print(f'School: {teacher["school_name"]}')
    print(f'Position: {teacher.get("position", "Teacher")}')
    
    # Create shared data with matching template AND teacher info
    shared_data = TeacherDocumentData(
        teacher['first_name'],
        teacher['last_name'],
        school_name=teacher['school_name'],
        school_template=district,
        position=teacher.get('position'),  # Use teacher's actual position
        hire_date=teacher.get('hire_date'),  # Use teacher's actual hire date
    )
    
    print(f'\nDocument Data:')
    print(f'  Employee ID: {shared_data.employee_id_formatted}')
    print(f'  District: {shared_data.district_name}')
    print(f'  Position: {shared_data.position}')
    print(f'  Template: {shared_data.school_template}')
    
    # Generate ID Card document
    png_data = generate_teacher_png(
        teacher['first_name'],
        teacher['last_name'],
        teacher['school_name'],
        doc_type='id_card',
        shared_data=shared_data,
        school_template=district
    )
    
    # Save to file
    filepath = output_dir / f'{district}_id_card.png'
    filepath.write_bytes(png_data)
    print(f'\nSaved: {filepath}')
    
    # Save teacher info
    info = {
        'district': district,
        'teacher': teacher,
        'document_info': {
            'employee_id': shared_data.employee_id_formatted,
            'school_name': shared_data.school_name,
            'district_name': shared_data.district_name,
            'position': shared_data.position,
            'full_name': shared_data.full_name,
        }
    }
    results.append(info)

# Save all info to JSON
info_path = output_dir / 'test_results.json'
info_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
print(f'\n{"="*50}')
print(f'Results saved to: {info_path}')
print(f'Documents saved to: {output_dir}')
print('Done!')
