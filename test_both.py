from one.img_generator import generate_both_documents
from one.name_generator import NameGenerator

name = NameGenerator.generate()
print(f"Generating for: {name['full_name']}")

result = generate_both_documents(name['first_name'], name['last_name'])

# Save both documents
open('test_schedule.png', 'wb').write(result['schedule'])
open('test_offer.png', 'wb').write(result['offer_letter'])

# Print shared student info
print("\n=== SHARED STUDENT INFO ===")
info = result['student_info']
print(f"Name: {info['full_name']}")
print(f"PSU ID: {info['psu_id']}")
print(f"Email: {info['email']}")
print(f"College: {info['college']}")
print(f"Major (Offer): {info['major']}")
print(f"Major (Schedule): {info['schedule_major']}")
print(f"Term: {info['term']}")

print("\nSaved: test_schedule.png and test_offer.png")
