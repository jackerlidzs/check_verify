"""Test ANC EISS API - using exact URL format"""
import httpx
import urllib.parse
from config.proxy_manager import get_proxy_url

# Use exact format from user's example
base_url = "https://ancexplorer.army.mil/proxy/proxy.ashx?https://wspublic.eiss.army.mil/v1/IssRetrieveServices.svc/search"

name = "ARTHUR"  # From user's example

# Build query exactly like user's example
query = f"primarylastname~{name}%2Ccemeteryid%3DALL"
full_url = f"{base_url}?AppId=Roi&q={query}&start=0&limit=10&sortColumn=PrimaryLastName%2CPrimaryFirstName%2CPrimaryMiddleName%2CDOB%2CDOD&sortOrder=asc&f=json"

print(f"Testing with: {name}")
print(f"URL: {full_url[:100]}...")
print()

r = httpx.get(full_url, proxy=get_proxy_url(), timeout=30)
print(f"Status: {r.status_code}")

if r.status_code == 200:
    data = r.json()
    records = data.get("SearchResult", {}).get("Records", [])
    print(f"Found {len(records)} records")
    print()
    
    # Show all records with their data
    for rec in records[:10]:
        first = rec.get("PRIMARYFIRSTNAME", "").strip()
        middle = rec.get("PRIMARYMIDDLENAME", "").strip()
        last = rec.get("PRIMARYLASTNAME", "").strip()
        dob = rec.get("DOB", "")
        dod = rec.get("DOD", "")
        branch = rec.get("BRANCHOFSERVICE", "")
        
        name_full = f"{first} {middle} {last}".strip()
        print(f"{name_full}")
        print(f"  DOB: {dob if dob else 'N/A'}")
        print(f"  DOD: {dod if dod else 'N/A'}")
        print(f"  Branch: {branch if branch else 'N/A'}")
        print()
else:
    print(f"Error: {r.text[:500]}")
