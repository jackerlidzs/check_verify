import httpx
from bs4 import BeautifulSoup
import re

# Springfield school districts URLs to try
urls = [
    # Illinois - District 186
    ('https://www.sps186.org/schools/staff/?schoolid=8', 'Springfield HS IL'),
    ('https://www.sps186.org/about/directory/', 'District 186 Directory'),
    # Missouri  
    ('https://www.sps.org/Page/2', 'Springfield MO SPS'),
    # Massachusetts
    ('https://www.springfieldpublicschools.com/domain/106', 'Springfield MA'),
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

all_found = {}
for url, name in urls:
    try:
        print(f"\nTrying: {name}")
        print(f"  URL: {url}")
        r = httpx.get(url, timeout=20, follow_redirects=True, headers=headers)
        print(f"  Status: {r.status_code}")
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Try multiple patterns
            names = []
            
            # Pattern 1: Staff name classes
            for elem in soup.select('.staffName, .name, .staff-name, .ui-staff-card-name'):
                n = elem.get_text(strip=True)
                if n:
                    names.append(n)
            
            # Pattern 2: Definition terms (often used in staff lists)
            for elem in soup.select('dt'):
                n = elem.get_text(strip=True)
                if n:
                    names.append(n)
            
            # Pattern 3: Table cells with names
            for row in soup.select('tr'):
                cells = row.select('td')
                if cells and len(cells) >= 1:
                    first_cell = cells[0].get_text(strip=True)
                    if first_cell and len(first_cell) > 3:
                        names.append(first_cell)
            
            # Clean names
            cleaned = []
            for n in names:
                n = re.sub(r'^(Mr\.|Ms\.|Mrs\.|Dr\.)\s*', '', n)
                if n and len(n) > 3 and len(n) < 50:
                    if not any(x in n.lower() for x in ['principal', 'secretary', 'click', 'email', 'phone', '@']):
                        cleaned.append(n)
            
            unique = list(dict.fromkeys(cleaned))
            if unique:
                print(f"  Found: {len(unique)} names")
                all_found[name] = unique[:20]
                for t in unique[:5]:
                    print(f"    - {t}")
            else:
                print(f"  No names found in HTML structure")
                # Print page title to understand what we got
                title = soup.select_one('title')
                if title:
                    print(f"  Page title: {title.get_text()}")
    except Exception as e:
        print(f"  Error: {str(e)[:60]}")

print(f"\n\n=== SUMMARY ===")
print(f"Total sources with data: {len(all_found)}")
for name, names in all_found.items():
    print(f"  {name}: {len(names)} names")
