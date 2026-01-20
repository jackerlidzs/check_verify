"""Test Proxy Connection

Run this script to verify proxy is working correctly.
Usage: python test_proxy.py
"""

import sys
sys.path.insert(0, '.')

from config.proxy_manager import ProxyManager

def test_proxy():
    pm = ProxyManager()
    
    print("=" * 50)
    print("PROXY TEST")
    print("=" * 50)
    
    # 1. Check config
    print(f"\n[1] Provider: {pm.active_provider_name}")
    print(f"    Enabled: {pm.enabled}")
    
    if not pm.enabled:
        print("\n[!] Proxy DISABLED - using direct connection")
        print("    Edit config/proxy.json to enable")
        return
    
    # 2. Show proxy URL (masked)
    url = pm.proxy_url
    if url:
        # Mask password
        masked = url[:40] + "..." if len(url) > 40 else url
        print(f"\n[2] Proxy URL: {masked}")
    
    # 3. Test connection
    print(f"\n[3] Testing connection...")
    ip, country = pm.detect_ip()
    
    if ip:
        country_upper = country.upper() if country else 'Unknown'
        print(f"\n    [OK] Proxy is WORKING!")
        print(f"    IP: {ip}")
        print(f"    Country: {country_upper}")
    else:
        print(f"\n    [X] Proxy NOT working")
        print(f"    Check credentials or provider status")

if __name__ == "__main__":
    test_proxy()
