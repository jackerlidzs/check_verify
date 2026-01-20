"""Test SheerID Org Search API - Better params"""
import httpx
import json
import urllib.parse

async def search_schools(query: str):
    """Search SheerID for K12 schools."""
    
    # Encode query
    q = urllib.parse.quote(query)
    
    # Different API patterns to try
    apis = [
        f"https://orgsearch.sheerid.net/rest/organization/search?q={q}&type=K12&country=US&limit=30",
        f"https://orgsearch.sheerid.net/rest/organization/search?name={q}&type=K12",
        f"https://orgsearch.sheerid.net/rest/organization?q={q}&type=K12",
    ]
    
    async with httpx.AsyncClient() as client:
        for url in apis:
            print(f"\nTrying: {url[:100]}...")
            try:
                resp = await client.get(url, timeout=15)
                print(f"Status: {resp.status_code}")
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    # Filter results containing query
                    if isinstance(data, list):
                        matching = [s for s in data if query.lower() in s.get('name', '').lower()]
                        print(f"Total: {len(data)}, Matching '{query}': {len(matching)}")
                        
                        if matching:
                            return matching
                        elif data:
                            return data[:10]
            except Exception as e:
                print(f"Error: {e}")
    
    return []

async def main():
    queries = ["Bronx High School Of Science", "Miami Beach Senior High", "Stuyvesant High"]
    
    for query in queries:
        print(f"\n{'='*50}")
        print(f"SEARCH: {query}")
        print('='*50)
        
        results = await search_schools(query)
        
        if results:
            print(f"\nFound {len(results)} matching schools:\n")
            for i, s in enumerate(results[:5]):
                print(f"{i+1}. {s.get('name')}")
                print(f"   ID: {s.get('id')} | Type: {s.get('type')}")
        else:
            print("No results")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
