"""
SheerID School Verification Tool

Checks which schools from our database appear in SheerID's dropdown.
This helps identify schools most likely to instant-verify.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
from datetime import datetime
import json
import time

os.chdir(Path(__file__).parent)

# Output file for verified schools
VERIFIED_SCHOOLS_FILE = Path("app/core/data/sheerid_verified_schools.json")

# Base SheerID URL (we'll test school search without submitting)
# We need a fresh verification URL to test
TEST_URL = "https://services.sheerid.com/verify/68d47554aa292d20b9bec8f7/?verificationId=695abb534ef52f78764a8718&redirectUrl=https%3A%2F%2Fchatgpt.com%2Fk12-verification"

def check_school_in_sheerid(page, school_name: str) -> dict:
    """Check if a school appears in SheerID's dropdown.
    
    Returns:
        dict with: {
            'school_name': original name,
            'found': True/False,
            'matches': list of matching schools from dropdown,
            'match_count': number of matches
        }
    """
    result = {
        'school_name': school_name,
        'found': False,
        'matches': [],
        'match_count': 0
    }
    
    try:
        # Find school input
        school_input = page.locator('#sid-teacher-school, input[id*="school"], input[placeholder*="school" i]').first
        if school_input.count() == 0:
            return result
        
        # Clear and type school name
        school_input.click()
        time.sleep(0.2)
        school_input.fill("")
        school_input.type(school_name[:15], delay=30)
        time.sleep(1.5)
        
        # Check dropdown
        options = page.locator('.sid-organization-list__item, [role="option"]')
        option_count = options.count()
        
        if option_count > 0:
            result['found'] = True
            result['match_count'] = option_count
            
            # Get text of each option (max 5)
            for i in range(min(option_count, 5)):
                try:
                    text = options.nth(i).inner_text()
                    result['matches'].append(text)
                except:
                    pass
        
        # Clear and escape
        page.keyboard.press("Escape")
        school_input.fill("")
        time.sleep(0.3)
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def verify_schools_from_database(url: str, max_schools: int = 50):
    """Check multiple schools from our database against SheerID.
    
    Args:
        url: Fresh SheerID verification URL
        max_schools: Maximum number of schools to check
    """
    from playwright.sync_api import sync_playwright
    
    # Load our schools
    from app.core.name_generator import load_priority_profiles, get_database_stats
    
    _, profiles_by_district = load_priority_profiles()
    stats = get_database_stats()
    
    print("="*60)
    print("🔍 SheerID School Verification Tool")
    print("="*60)
    print(f"Total schools in our database: {len(stats['schools'])}")
    print(f"Checking up to {max_schools} schools...")
    print("="*60)
    
    # Get unique schools
    unique_schools = list(stats['schools'].keys())[:max_schools]
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'verified_schools': [],
        'not_found_schools': [],
        'total_checked': 0
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Headless for speed
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(30000)
        
        try:
            print(f"\n📍 Loading SheerID page...")
            page.goto(url, wait_until='networkidle')
            time.sleep(2)
            
            # Wait for form
            try:
                page.wait_for_selector('input', timeout=10000)
            except:
                print("❌ Form not found!")
                return results
            
            print("\n🔍 Checking schools...\n")
            
            for i, school_name in enumerate(unique_schools):
                print(f"[{i+1}/{len(unique_schools)}] {school_name[:40]}...", end=" ")
                
                result = check_school_in_sheerid(page, school_name)
                results['total_checked'] += 1
                
                if result['found']:
                    print(f"✅ FOUND ({result['match_count']} matches)")
                    results['verified_schools'].append({
                        'name': school_name,
                        'match_count': result['match_count'],
                        'matches': result['matches']
                    })
                else:
                    print("❌ NOT FOUND")
                    results['not_found_schools'].append(school_name)
                
                # Small delay between checks
                time.sleep(0.5)
            
        finally:
            browser.close()
    
    # Summary
    print("\n" + "="*60)
    print("📊 RESULTS SUMMARY")
    print("="*60)
    print(f"Total checked: {results['total_checked']}")
    print(f"✅ Found in SheerID: {len(results['verified_schools'])}")
    print(f"❌ Not found: {len(results['not_found_schools'])}")
    print(f"Success rate: {len(results['verified_schools'])/results['total_checked']*100:.1f}%")
    
    # Save results
    VERIFIED_SCHOOLS_FILE.parent.mkdir(exist_ok=True)
    with open(VERIFIED_SCHOOLS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Results saved to: {VERIFIED_SCHOOLS_FILE}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify schools against SheerID database')
    parser.add_argument('--url', type=str, help='SheerID verification URL', 
                        default=TEST_URL)
    parser.add_argument('--max', type=int, default=20, help='Max schools to check')
    
    args = parser.parse_args()
    
    print(f"\n⚠️ Using URL: {args.url[:60]}...")
    print("⚠️ Make sure this is a FRESH verification URL!\n")
    
    input("Press Enter to start checking...")
    
    results = verify_schools_from_database(args.url, args.max)
    
    if results['verified_schools']:
        print("\n✅ Schools found in SheerID:")
        for school in results['verified_schools'][:10]:
            print(f"   - {school['name']}")
