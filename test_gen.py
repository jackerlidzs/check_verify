from one.img_generator import generate_image
from one.name_generator import NameGenerator

name = NameGenerator.generate()
img = generate_image(name['first_name'], name['last_name'], doc_type='enrollment_letter')
open('test_final.png', 'wb').write(img)
print(f"Generated for: {name['full_name']}")
