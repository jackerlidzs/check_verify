"""Debug NGL HTML structure"""
import httpx

# Search for SMITH
form_data = {
    "lastName": "SMITH",
    "lastNameOpt": "1",
    "firstName": "",
    "firstNameOpt": "1",
    "middleName": "",
    "middleNameOpt": "1",
    "p_birthMM": "",
    "p_birthYY": "",
    "p_deathMM": "",
    "p_deathYY": "",
    "cemetery": "",
    "nglUP": "1",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
}

print("Fetching NGL results...")
r = httpx.post("https://gravelocator.cem.va.gov/ngl/result", data=form_data, headers=headers, timeout=30, follow_redirects=True)
print(f"Status: {r.status_code}")

# Save HTML for analysis
with open("ngl_debug.html", "w", encoding="utf-8") as f:
    f.write(r.text)

print(f"Saved {len(r.text)} bytes to ngl_debug.html")

# Show a portion of the HTML
print("\n=== HTML Sample (lines with veteran info) ===")
lines = r.text.split("\n")
for i, line in enumerate(lines):
    # Look for lines with veteran-related content
    if any(x in line.lower() for x in ["smith", "army", "navy", "birth", "death", "veteran"]):
        print(f"Line {i}: {line[:200]}...")
        if i > 100:  # Limit output
            break
