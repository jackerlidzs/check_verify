"""Generate document for manual upload"""
from one.img_generator import generate_image, generate_psu_email, generate_psu_id
from one.name_generator import NameGenerator, generate_birth_date

# Generate student info
name = NameGenerator.generate()
psu_id = generate_psu_id()
email = generate_psu_email(name['first_name'], name['last_name'])
dob = generate_birth_date()

# Generate document
img = generate_image(name['first_name'], name['last_name'])
open('manual_upload_doc.png', 'wb').write(img)

# Print info
print('='*50)
print('STUDENT PROFILE (dien vao form):')
print('='*50)
print(f"First Name: {name['first_name']}")
print(f"Last Name: {name['last_name']}")
print(f"Email: {email}")
print(f"Birth Date: {dob}")
print(f"School: Pennsylvania State University-Main Campus")
print('='*50)
print('Document saved: manual_upload_doc.png')
