"""Filter eligible veterans - birthdate after 1945"""
import json
from datetime import datetime
from pathlib import Path

# Load all data
files = ['military/data/ngl_veterans.json', 'military/data/anc_veterans.json', 'military/data/veterans_usa.json']
all_vets = []
for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as fp:
            all_vets.extend(json.load(fp))
    except:
        pass

print(f'Total veterans: {len(all_vets)}')

# Filter by birthdate (born after 1945 = under 80)
eligible = []
for v in all_vets:
    birth = v.get('birth', '')
    if birth:
        try:
            year = int(birth.split('/')[0]) if '/' in birth else 0
            if year >= 1945:
                eligible.append(v)
        except:
            pass

print(f'Born after 1945 (under 80): {len(eligible)}')

# Further filter - born after 1960 (under 65)
young = [v for v in eligible if int(v.get('birth', '0').split('/')[0]) >= 1960]
print(f'Born after 1960 (under 65): {len(young)}')

# Even younger - born after 1970 (under 55)
very_young = [v for v in eligible if int(v.get('birth', '0').split('/')[0]) >= 1970]
print(f'Born after 1970 (under 55): {len(very_young)}')

# Show samples
print()
print('Sample eligible (born after 1960):')
for v in young[:15]:
    name = v.get('name', '')[:25]
    birth = v.get('birth', '')
    death = v.get('death', '')
    print(f"  {name:25} | Birth: {birth} | Death: {death}")

# Save eligible
if eligible:
    with open('military/data/eligible_veterans.json', 'w', encoding='utf-8') as f:
        json.dump(eligible, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(eligible)} eligible veterans to military/data/eligible_veterans.json")
