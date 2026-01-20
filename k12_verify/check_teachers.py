import json

with open('app/core/data/real_teachers.json', 'r') as f:
    data = json.load(f)

print(f"Total teachers: {len(data)}")

# Count by email domain
domains = {}
for t in data:
    email = t.get('email', '')
    domain = email.split('@')[-1] if '@' in email else 'unknown'
    domains[domain] = domains.get(domain, 0) + 1

print("\nEmail domains:")
for domain, count in sorted(domains.items(), key=lambda x: -x[1])[:10]:
    print(f"  {domain}: {count}")

# Filter priority districts
nyc = [t for t in data if '@schools.nyc.gov' in t.get('email', '').lower()]
miami = [t for t in data if '@dadeschools.net' in t.get('email', '').lower()]
springfield = [t for t in data if 'springfield' in t.get('email', '').lower() 
               or 'kickapoo' in t.get('school_name', '').lower()]

print(f"\nPriority districts in real_teachers.json:")
print(f"  NYC DOE: {len(nyc)}")
print(f"  Miami-Dade: {len(miami)}")
print(f"  Springfield: {len(springfield)}")
