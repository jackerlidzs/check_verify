"""Check and fix NGL name format"""
import json
import re

# Load data
with open('military/data/ngl_veterans.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total records: {len(data)}")
print()

# Sample names
print("First 20 names:")
for d in data[:20]:
    print(f"  {d['name']}")

print()

# Find problematic names
print("Problematic names (only initials, JR/SR issues, etc):")
problems = []
for d in data:
    name = d['name']
    parts = name.split()
    
    # Check for issues:
    # 1. Too short (1-2 chars only)
    # 2. JR/SR in wrong position
    # 3. Only initials
    
    if len(parts) >= 2:
        # Check if all parts except last are single letters/initials
        all_initials = all(len(p) <= 2 for p in parts[:-1])
        if all_initials and len(parts) > 2:
            problems.append(name)
        
        # Check JR/SR in middle
        for i, p in enumerate(parts[:-1]):
            if p in ['JR', 'SR', 'II', 'III', 'IV']:
                if i < len(parts) - 1:  # Not at end
                    problems.append(name)
                    break

print(f"Found {len(problems)} problematic names")
for p in problems[:20]:
    print(f"  {p}")
