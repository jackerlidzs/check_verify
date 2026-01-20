import httpx
from bs4 import BeautifulSoup
import json
import time
import re

# Miami-Dade schools to scrape
miami_schools = [
    {"name": "Homestead Senior High", "id": "7161", "city": "Homestead"},
    {"name": "Miami Senior High", "id": "7241", "city": "Miami"},
    {"name": "Southwest Miami Senior High", "id": "7721", "city": "Miami"},
    {"name": "Ferguson Senior High", "id": "7041", "city": "Miami"},
    {"name": "Killian Senior High", "id": "7371", "city": "Miami"},
    {"name": "Braddock Senior High", "id": "6061", "city": "Miami"},
    {"name": "Coral Reef Senior High", "id": "6171", "city": "Miami"},
]

def scrape_miami_school(school_info):
    """Scrape teachers from Miami-Dade school staff page"""
    base_urls = [
        f"https://www.{school_info['name'].lower().replace(' ', '')}.org/apps/staff/",
        f"https://{school_info['name'].lower().replace(' ', '-')}.dadeschools.net/staff",
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for url in base_urls:
        try:
            print(f"  Trying: {url}")
            r = httpx.get(url, timeout=20, follow_redirects=True, headers=headers)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                
                names = []
                for elem in soup.select('.name, .staff-name, dt, .user-name, .staffPhotoWrapperRound dt'):
                    name = elem.get_text(strip=True)
                    if name and len(name) > 3 and len(name) < 50:
                        # Clean name - remove titles
                        name = re.sub(r'^(Mr\.|Ms\.|Mrs\.|Dr\.)\s*', '', name)
                        if name and not any(x in name.lower() for x in ['principal', 'secretary', 'click']):
                            names.append(name)
                
                if names:
                    print(f"  Found {len(names)} names")
                    return names[:15]
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    return []

# Scrape each school
all_results = {}
for school in miami_schools:
    print(f"\n=== {school['name']} ===")
    names = scrape_miami_school(school)
    if names:
        all_results[school['name']] = names
        for n in names[:5]:
            print(f"  - {n}")
    time.sleep(1)

print(f"\n\nTotal schools with data: {len(all_results)}")
