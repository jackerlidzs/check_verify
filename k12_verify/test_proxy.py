"""Test DataImpulse Proxy Connection"""
from dotenv import load_dotenv
load_dotenv(override=True)

import os
import httpx

print("=" * 50)
print("DataImpulse Proxy Test")
print("=" * 50)

# Load config
host = os.getenv('PROXY_HOST', 'gw.dataimpulse.com')
port = os.getenv('PROXY_PORT', '10000')
user = os.getenv('PROXY_USER', '')
passwd = os.getenv('PROXY_PASS', '')
country = os.getenv('PROXY_COUNTRY', 'us')
state = os.getenv('PROXY_STATE', 'california,florida,newyork,texas')
session = os.getenv('PROXY_SESSION', 'test123')

print(f"Host: {host}")
print(f"Port: {port}")
print(f"User: {user[:10]}..." if user else "User: NOT SET")
print(f"Country: {country}")
print(f"State: {state}")
print(f"Session: {session}")

if not user or not passwd:
    print("\n[ERROR] PROXY_USER or PROXY_PASS not set in .env")
    exit(1)

# Build proxy URL with DataImpulse format
# Format: user__cr.{country};state.{states};sess.{session}:pass@host:port
username = f"{user}__cr.{country};state.{state}"
if session and session != "default":
    username += f";sess.{session}"

proxy_url = f"http://{username}:{passwd}@{host}:{port}"

print(f"\nProxy URL: {proxy_url[:80]}...")
print("\nConnecting...")

try:
    client = httpx.Client(proxy=proxy_url, timeout=30)
    response = client.get('https://api.ipify.org')
    
    if response.status_code == 200:
        ip = response.text.strip()
        print(f"\n[OK] SUCCESS!")
        print(f"Your IP: {ip}")
    else:
        print(f"\n[ERROR] HTTP Error: {response.status_code}")
        print(response.text)
    
    client.close()

except Exception as e:
    print(f"\n[ERROR] Connection Error: {e}")

