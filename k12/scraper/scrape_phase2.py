import httpx
from bs4 import BeautifulSoup
import json
import time

# Schools to scrape for Phase 2 remaining
schools_to_scrape = [
    {
        "name": "Edward R. Murrow High School",
        "url": "https://www.ermurrowhs.org/apps/staff/",
        "school_id": "K525",
        "city": "Brooklyn"
    },
    {
        "name": "Benjamin N. Cardozo High School", 
        "url": "https://www.cardozohigh.org/apps/staff/",
        "school_id": "Q555",
        "city": "Bayside"
    },
    {
        "name": "Forest Hills High School",
        "url": "https://www.foresthillshs.org/apps/staff/",
        "school_id": "Q440",
        "city": "Forest Hills"
    }
]

def scrape_school(school_info):
    """Scrape teachers from a school staff page"""
    teachers = []
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = httpx.get(school_info["url"], timeout=30, follow_redirects=True, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Try multiple selectors
        found_names = []
        
        # Pattern 1: Staff cards with name elements
        for elem in soup.select('.name, .staff-name, dt, .user-name'):
            name = elem.get_text(strip=True)
            if name and len(name) > 3 and len(name) < 50 and not any(x in name.lower() for x in ['principal', 'secretary', 'click', 'view']):
                found_names.append(name)
        
        # Pattern 2: Table rows
        if len(found_names) < 5:
            for row in soup.select('table tr'):
                cells = row.select('td')
                if len(cells) >= 1:
                    name = cells[0].get_text(strip=True)
                    if name and len(name) > 3 and len(name) < 50:
                        found_names.append(name)
        
        # Remove duplicates and limit
        seen = set()
        unique_names = []
        for name in found_names:
            if name not in seen:
                seen.add(name)
                unique_names.append(name)
        
        print(f"Found {len(unique_names)} names from {school_info['name']}")
        for name in unique_names[:15]:
            print(f"  - {name}")
        
        return unique_names[:15]
        
    except Exception as e:
        print(f"Error scraping {school_info['name']}: {e}")
        return []

# Scrape each school
for school in schools_to_scrape:
    print(f"\n=== Scraping {school['name']} ===")
    names = scrape_school(school)
    time.sleep(2)  # Be nice to servers
