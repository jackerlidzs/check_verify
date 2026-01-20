"""
Improved 3-step verification test with proper page validation and logging.
Checks actual page content before each step and logs browser info.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
from datetime import datetime
import time
import random

# Screenshots folder
SCREENSHOTS_DIR = Path(r"C:\Users\jacke\.gemini\antigravity\brain\be827772-77bf-4f48-91ad-569cf624d56b")

# SheerID URL to test - needs to be a fresh verification URL
TEST_URL = "https://services.sheerid.com/verify/68d47554aa292d20b9bec8f7/?verificationId=695aa9a231835a5e0a8a45fe&redirectUrl=https%3A%2F%2Fchatgpt.com%2Fk12-verification"

def screenshot(page, name: str) -> Path:
    """Take screenshot."""
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"test_{timestamp}_{name}.png"
    path = SCREENSHOTS_DIR / filename
    page.screenshot(path=str(path))
    print(f"    📸 Screenshot: {filename}")
    return path

def log_page_info(page, step_name: str):
    """Log detailed page information."""
    print(f"\n    [PAGE INFO - {step_name}]")
    print(f"    URL: {page.url}")
    print(f"    Title: {page.title()}")
    
    # Get visible text summary
    try:
        body_text = page.inner_text('body')[:500].replace('\n', ' ')
        print(f"    Content preview: {body_text[:200]}...")
    except:
        print("    Content: (could not get)")
    
    # Check for common elements
    checks = {
        'SheerID Form': '#sid-first-name',
        'School Input': '#sid-teacher-school',
        'File Upload': 'input[type="file"]',
        'Submit Button': 'button[type="submit"]',
        'Error Message': '[class*="error"]',
        'Login Prompt': 'text=log in',
        'Status Verified': 'text=Status verified',
    }
    
    print("    Elements found:")
    for name, selector in checks.items():
        count = page.locator(selector).count()
        if count > 0:
            print(f"      ✓ {name}: {count}")
    print()

def run_test():
    from playwright.sync_api import sync_playwright
    from app.core.name_generator import generate_teacher_info
    from app.core import config
    from app import config as app_config
    
    # Generate teacher data
    district = random.choice(list(app_config.DISTRICTS.keys()))
    teacher = generate_teacher_info(district=district)
    school = config.SCHOOLS[config.DEFAULT_SCHOOL_ID]
    
    print("="*60)
    print("📋 TEST DATA")
    print("="*60)
    print(f"  Name: {teacher['first_name']} {teacher['last_name']}")
    print(f"  Email: {teacher['email']}")
    print(f"  School: {school['name']}")
    print(f"  URL: {TEST_URL}")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        page.set_default_timeout(30000)
        
        try:
            # ========================================
            # STEP 1: Navigate and Check Page
            # ========================================
            print("\n" + "="*60)
            print("STEP 1: Navigate and fill form")
            print("="*60)
            
            print(f"  Navigating to: {TEST_URL}")
            page.goto(TEST_URL, wait_until='networkidle')
            time.sleep(2)
            
            # Wait for page to fully render (SheerID uses React)
            print("  Waiting for form to load...")
            
            # Try different form selectors (SheerID may use different IDs)
            form_selectors = [
                '#sid-first-name',
                'input[name="firstName"]',
                'input[placeholder*="First"]',
                '#firstName',
                'input[data-testid="first-name"]',
            ]
            
            form_found = False
            first_name_input = None
            
            for selector in form_selectors:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    first_name_input = page.locator(selector).first
                    if first_name_input.count() > 0:
                        form_found = True
                        print(f"    ✓ Form found with: {selector}")
                        break
                except:
                    continue
            
            # Log page info
            log_page_info(page, "After Navigation")
            
            # Check for login page
            has_login = 'log in' in page.inner_text('body').lower()
            if has_login:
                print("  ⚠️ WARNING: Page shows 'log in' - may need fresh URL!")
                screenshot(page, "ERROR_login_required")
                print("\n  ❌ Cannot proceed - page requires login")
                input("\nPress Enter to close...")
                return
            
            if not form_found:
                print("  ⚠️ WARNING: Form not found!")
                screenshot(page, "ERROR_no_form")
                
                # List all inputs for debugging
                print("\n  All input elements on page:")
                inputs = page.locator('input').all()
                for i, inp in enumerate(inputs[:10]):
                    inp_id = inp.get_attribute('id') or '(no id)'
                    inp_name = inp.get_attribute('name') or '(no name)'
                    inp_type = inp.get_attribute('type') or 'text'
                    inp_placeholder = inp.get_attribute('placeholder') or ''
                    print(f"    {i+1}. id={inp_id}, name={inp_name}, type={inp_type}, placeholder={inp_placeholder}")
                
                input("\nPress Enter to close...")
                return
            
            print("  ✓ Form detected - filling...")
            
            # Fill form
            page.locator('#sid-first-name').fill(teacher['first_name'])
            print(f"    Filled first name: {teacher['first_name']}")
            
            page.locator('#sid-last-name').fill(teacher['last_name'])
            print(f"    Filled last name: {teacher['last_name']}")
            
            page.locator('#sid-email').fill(teacher['email'])
            print(f"    Filled email: {teacher['email']}")
            
            # School
            school_input = page.locator('#sid-teacher-school')
            school_input.click()
            time.sleep(0.3)
            school_input.type(school['name'][:12], delay=30)
            time.sleep(2)
            
            options = page.locator('.sid-organization-list__item')
            opt_count = options.count()
            print(f"    School dropdown: {opt_count} options")
            
            if opt_count > 0:
                page.keyboard.press("ArrowDown")
                time.sleep(0.2)
                page.keyboard.press("Enter")
            page.keyboard.press("Escape")
            print(f"    Selected school: {school['name']}")
            
            time.sleep(1)
            log_page_info(page, "After Form Fill")
            step1_img = screenshot(page, "step1_form_filled")
            print(f"\n  ✅ STEP 1 COMPLETE")
            
            # Submit
            print("\n  Submitting form...")
            submit_btn = page.locator('button[type="submit"]').first
            if submit_btn.count() > 0:
                submit_btn.click()
            else:
                page.keyboard.press("Enter")
            time.sleep(4)
            
            # ========================================
            # STEP 2: Check Result After Submit
            # ========================================
            print("\n" + "="*60)
            print("STEP 2: Check result after submit")
            print("="*60)
            
            log_page_info(page, "After Submit")
            
            # Check for document upload
            file_input = page.locator('input[type="file"]')
            if file_input.count() > 0:
                print("  📄 Document upload required!")
                step2a_img = screenshot(page, "step2_doc_required")
                
                # Generate and upload badge
                from app.core.badge_generator import create_teacher_badge
                badge_path = create_teacher_badge(teacher, school)
                
                if badge_path and badge_path.exists():
                    print(f"    Generated badge: {badge_path.name}")
                    file_input.set_input_files(str(badge_path))
                    time.sleep(2)
                    
                    log_page_info(page, "After Upload")
                    step2b_img = screenshot(page, "step2_doc_uploaded")
                    
                    # Submit
                    print("    Submitting document...")
                    for selector in ['button[type="submit"]', 'button:has-text("Submit")']:
                        btn = page.locator(selector).first
                        if btn.count() > 0:
                            btn.click()
                            break
                    time.sleep(4)
            else:
                print("  ℹ️ No document upload needed")
                screenshot(page, "step2_no_doc_needed")
            
            # ========================================
            # STEP 3: Final Result
            # ========================================
            print("\n" + "="*60)
            print("STEP 3: Final result")
            print("="*60)
            
            time.sleep(3)
            log_page_info(page, "Final")
            step3_img = screenshot(page, "step3_final_result")
            
            # Analyze result
            page_text = page.inner_text('body').lower()
            url = page.url
            
            print("\n  Result Analysis:")
            if 'status verified' in page_text:
                print("    🎉 SUCCESS: 'Status verified' found!")
            elif "you've successfully verified" in page_text:
                print("    🎉 SUCCESS: Verification confirmed!")
            elif 'log in' in page_text:
                print("    ❌ FAILED: Login required")
            elif 'error' in page_text:
                print("    ❌ FAILED: Error on page")
            elif 'chatgpt.com' in url:
                print(f"    ⚠️ Redirected to ChatGPT: {url}")
            else:
                print("    ⏳ Status unclear")
            
            print("\n" + "="*60)
            print("TEST COMPLETE - Check screenshots")
            print("="*60)
            
            input("\nPress Enter to close browser...")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            screenshot(page, "ERROR_exception")
            import traceback
            traceback.print_exc()
            input("\nPress Enter to close...")
            
        finally:
            browser.close()

if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    run_test()
