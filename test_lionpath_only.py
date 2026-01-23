from one.img_generator import generate_image
from one.name_generator import NameGenerator

name = NameGenerator.generate()
print(f"Generating LionPATH for: {name['full_name']}")

# Generate only LionPATH schedule (independent, not matched with offer)
img_bytes = generate_image(name['first_name'], name['last_name'], doc_type='schedule')

open('test_lionpath_only.png', 'wb').write(img_bytes)
print("Saved: test_lionpath_only.png")
