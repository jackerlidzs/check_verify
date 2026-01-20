import json

with open('app/core/data/real_teachers.json', 'r') as f:
    data = json.load(f)

# Filter priority districts
priority = {
    "nyc_doe": [],
    "miami_dade": [],
    "springfield_high": []
}

for t in data:
    email = t.get('email', '').lower()
    school = t.get('school_name', '').lower()
    
    if '@schools.nyc.gov' in email:
        priority["nyc_doe"].append(t)
    elif '@dadeschools.net' in email:
        priority["miami_dade"].append(t)
    elif any(d in email for d in ["springfield", "sps186", "sps.org"]) or \
         any(s in school for s in ["springfield", "kickapoo", "lanphier"]):
        priority["springfield_high"].append(t)

# Save
with open('app/core/data/k12_teacher_info.json', 'w') as f:
    json.dump(priority, f, indent=2)

print("Created k12_teacher_info.json")
for district, teachers in priority.items():
    print(f"  {district}: {len(teachers)} teachers")

# Show samples
for district in priority:
    t = priority[district][0] if priority[district] else None
    if t:
        print(f"\nSample {district}: {t['first_name']} {t['last_name']} ({t['email']})")
