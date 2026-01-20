"""
Sync Playwright Browser Verifier (for FastAPI/Windows compatibility)

Runs all Playwright operations synchronously within a thread.
Called from async context via run_in_executor.
"""
import os
import re
import random
import time
import logging
import traceback
from typing import Dict, Optional, Callable
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

logger = logging.getLogger(__name__)


def create_blank_image(output_path: Path) -> bool:
    """Create a blank white image for document retry strategy."""
    try:
        from PIL import Image
        img = Image.new('RGB', (800, 600), color='white')
        img.save(output_path)
        return True
    except ImportError:
        # Create minimal PNG without PIL
        try:
            import struct
            import zlib
            
            # Minimal 1x1 white PNG
            def png_chunk(chunk_type, data):
                chunk_len = struct.pack('>I', len(data))
                chunk_crc = struct.pack('>I', zlib.crc32(chunk_type + data) & 0xffffffff)
                return chunk_len + chunk_type + data + chunk_crc
            
            signature = b'\x89PNG\r\n\x1a\n'
            ihdr = struct.pack('>IIBBBBB', 100, 100, 8, 2, 0, 0, 0)
            idat = zlib.compress(b'\x00' + b'\xff\xff\xff' * 100 * 100)
            
            with open(output_path, 'wb') as f:
                f.write(signature)
                f.write(png_chunk(b'IHDR', ihdr))
                f.write(png_chunk(b'IDAT', idat))
                f.write(png_chunk(b'IEND', b''))
            return True
        except:
            return False
    except Exception:
        return False


def run_sync_verification(
    sheerid_url: str,
    teacher_data: Dict,
    school: Dict,
    proxy_config: Dict = None,
    status_callback: Callable = None,
    headless: bool = True,
    keep_open: bool = False
) -> Dict:
    """
    Run full browser verification using sync Playwright.
    
    This function runs in a separate thread via ThreadPoolExecutor
    to avoid Windows event loop subprocess issues.
    """
    def log(msg):
        if status_callback:
            status_callback("SYNC", msg)
        logger.info(msg)
    
    if sync_playwright is None:
        return {'success': False, 'error': True, 'message': 'Playwright not installed'}
    
    browser = None
    pw = None
    
    try:
        log("🚀 Starting sync Playwright...")
        pw = sync_playwright().start()
        log("✅ Playwright started")
        
        # Proxy config
        proxy = None
        if proxy_config and proxy_config.get('server'):
            proxy = proxy_config
            log(f"🌐 Using proxy: {proxy['server'][:30]}...")
        
        # Launch browser
        log("🌐 Launching browser...")
        browser = pw.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        context = browser.new_context(
            proxy=proxy,
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
        )
        
        page = context.new_page()
        page.set_default_timeout(15000)
        log("✅ Browser ready")
        
        # Get IP
        try:
            page.goto('https://api.ipify.org?format=json', timeout=10000)
            import json
            ip_data = json.loads(page.inner_text('body'))
            log(f"🇺🇸 IP: {ip_data.get('ip', 'Unknown')}")
        except:
            log("⚠️ Could not get IP")
        
        # Navigate to SheerID
        log(f"📍 Navigating to SheerID...")
        page.goto(sheerid_url, timeout=60000, wait_until='networkidle')
        
        # Human-like delay after page load (increased from 2s to 4-6s for anti-detection)
        initial_delay = random.uniform(4.0, 6.0)
        log(f"⏳ Waiting {initial_delay:.1f}s (simulating page reading)...")
        time.sleep(initial_delay)
        
        # Fill form
        log("📝 Filling form...")
        
        # Wait for form to be ready
        try:
            page.wait_for_selector('input', timeout=10000)
        except:
            log("⚠️ Form inputs not found")
        
        # Helper to find and fill input
        def fill_input(selectors: list, value: str, field_name: str) -> bool:
            for selector in selectors:
                try:
                    inp = page.locator(selector).first
                    if inp.count() > 0 and inp.is_visible():
                        inp.click()
                        # Human-like delay between click and type (increased from 0.1s)
                        time.sleep(random.uniform(0.3, 0.8))
                        inp.fill(value)
                        # Delay after filling (simulate reading/checking)
                        time.sleep(random.uniform(0.5, 1.2))
                        log(f"  ✓ {field_name}: {value[:20]}...")
                        return True
                except:
                    continue
            log(f"  ❌ {field_name}: not found")
            return False
        
        # School name (often first on form) - CHECK DROPDOWN FIRST
        school_name = teacher_data.get('school_name', school['name'])[:20]
        school_filled = fill_input([
            '#sid-teacher-school',
            'input[id*="school"]',
            'input[name*="school"]',
            'input[placeholder*="school" i]',
            'input[aria-label*="school" i]',
        ], school_name, "School")
        
        # CRITICAL: Wait for school dropdown and validate
        school_in_database = False
        if school_filled:
            time.sleep(1.5)  # Wait for dropdown to load
            options = page.locator('.sid-organization-list__item, [role="option"], li[data-option]')
            option_count = options.count()
            
            if option_count > 0:
                log(f"  ✓ School found in SheerID ({option_count} matches)")
                school_in_database = True
                page.keyboard.press("ArrowDown")
                time.sleep(0.1)
                page.keyboard.press("Enter")
            else:
                log(f"  ⚠️ School NOT in SheerID dropdown - may require email verification!")
                page.keyboard.press("Escape")
            time.sleep(0.3)
        
        # Log warning if school not found
        if not school_in_database:
            log("  ⚠️ WARNING: School not in database - high chance of email verification")
        
        # First name
        fill_input([
            '#sid-first-name',
            'input[id*="first"]',
            'input[name*="first"]', 
            'input[placeholder*="First" i]',
        ], teacher_data['first_name'], "First name")
        
        # Last name
        fill_input([
            '#sid-last-name',
            'input[id*="last"]',
            'input[name*="last"]',
            'input[placeholder*="Last" i]',
        ], teacher_data['last_name'], "Last name")
        
        # Email
        fill_input([
            '#sid-email',
            'input[id*="email"]',
            'input[name*="email"]',
            'input[type="email"]',
            'input[placeholder*="email" i]',
        ], teacher_data['email'], "Email")
        
        # Human-like delay before submit (increased from 0.5s to 3-5s for anti-detection)
        pre_submit_delay = random.uniform(3.0, 5.0)
        log(f"⏳ Waiting {pre_submit_delay:.1f}s before submit (simulating form review)...")
        time.sleep(pre_submit_delay)
        log(f"✅ Form filled: {teacher_data['first_name']} {teacher_data['last_name']}")
        
        # Submit form
        log("📤 Submitting form...")
        submit_btns = [
            'button[type="submit"]',
            'button:has-text("Verify")',
            'button:has-text("Continue")',
        ]
        for selector in submit_btns:
            btn = page.locator(selector).first
            if btn.count() > 0:
                btn.click()
                time.sleep(2)
                break
        else:
            page.keyboard.press("Enter")
            time.sleep(2)
        
        log("✅ Form submitted")
        
        # Wait and check result
        time.sleep(3)
        
        # Helper function to check if verification was successful
        def check_verification_status(page) -> dict:
            """Check page for verification status."""
            try:
                current_url = page.url
                page_text = page.inner_text('body').lower() if page.locator('body').count() > 0 else ""
                
                # Check for email verification page FIRST (most common)
                if 'check your email' in page_text or 'email has been sent' in page_text:
                    return {'verified': False, 'email_sent': True, 'message': 'Email verification required'}
                
                # Check for error/rejection
                if 'unable to verify' in page_text or 'verification failed' in page_text:
                    return {'verified': False, 'error': True, 'message': 'Verification rejected'}
                
                if 'please log in' in page_text:
                    return {'verified': False, 'error': True, 'message': 'Login required'}
                
                # Check for "Status verified" message (actual success)
                if 'status verified' in page_text or "you've successfully verified" in page_text:
                    return {'verified': True, 'url': current_url}
                
                # Check URL indicates success (redirected to ChatGPT)
                if 'chatgpt.com' in current_url:
                    return {'verified': True, 'url': current_url}
                
                # Check for Continue to OpenAI button
                if page.locator('text=Continue to OpenAI').count() > 0:
                    return {'verified': True, 'url': current_url}
                
                # Check for document upload required
                if page.locator('input[type="file"]').count() > 0:
                    return {'verified': False, 'doc_required': True, 'message': 'Document upload required'}
                
                return {'verified': False}
            except:
                return {'verified': False}
        
        status = check_verification_status(page)
        if status.get('verified'):
            log("✅ VERIFICATION SUCCESSFUL! (Status verified)")
            log(f"🔗 {status.get('url', page.url)}")
            return {
                'success': True,
                'redirectUrl': status.get('url', page.url),
                'teacher': teacher_data
            }
        
        # Check for doc upload
        try:
            page.wait_for_selector('input[type="file"]', timeout=5000)
            log("📄 Document upload required")
            
            # Smart document retry strategy
            max_retries = 3
            doc_uploaded = False
            
            for attempt in range(1, max_retries + 1):
                log(f"📝 Document attempt {attempt}/{max_retries}")
                
                doc_path = None
                
                if attempt == 1:
                    # First attempt: Try existing docs or generate badge
                    project_root = Path(__file__).parent.parent.parent.parent
                    doc_paths = [
                        Path(__file__).parent / "generated" / "teacher_badge.png",
                        Path(__file__).parent / "test_payslip.png",
                        project_root / "k12" / "test_payslip.png",
                    ]
                    
                    for p in doc_paths:
                        if p.exists():
                            doc_path = p
                            log(f"📁 Found: {p.name}")
                            break
                    
                    # Generate badge if no doc found
                    if not doc_path:
                        log("🎨 Generating Teacher Badge...")
                        try:
                            from .badge_generator import create_teacher_badge
                            badge_path = create_teacher_badge(teacher_data, school)
                            if badge_path and badge_path.exists():
                                doc_path = badge_path
                                log(f"✅ Badge created")
                        except Exception as e:
                            log(f"⚠️ Badge failed: {e}")
                else:
                    # Retry: Use blank white image (trick from linux.do)
                    blank_path = Path(__file__).parent / "generated" / f"blank_{attempt}.png"
                    blank_path.parent.mkdir(exist_ok=True)
                    if create_blank_image(blank_path):
                        doc_path = blank_path
                        log("📄 Using blank image (retry strategy)")
                
                if doc_path and doc_path.exists():
                    # Upload document
                    file_input = page.locator('input[type="file"]').first
                    if file_input.count() > 0:
                        file_input.set_input_files(str(doc_path))
                        log("📤 Document uploaded")
                        time.sleep(2)
                        
                        # Submit
                        for selector in ['button[type="submit"]', 'button:has-text("Submit")', 'button:has-text("Continue")']:
                            btn = page.locator(selector).first
                            if btn.count() > 0:
                                btn.click()
                                break
                        else:
                            page.keyboard.press("Enter")
                        
                        time.sleep(3)
                        
                        # Check if verification succeeded after doc upload
                        doc_status = check_verification_status(page)
                        if doc_status.get('verified'):
                            log("✅ Document accepted!")
                            doc_uploaded = True
                            break
                        elif doc_status.get('error'):
                            log(f"❌ Document rejected: {doc_status.get('message', 'Unknown')}")
                        else:
                            log("⏳ Document submitted, checking result...")
                            # Check if still on upload page
                            if page.locator('input[type="file"]').count() > 0:
                                log("🔄 Still asking for document, retrying...")
                                continue
                            else:
                                doc_uploaded = True
                                break
                else:
                    log("⚠️ No document available for this attempt")
            
            if not doc_uploaded and max_retries > 0:
                log(f"⚠️ All {max_retries} document attempts failed")
                
        except:
            log("ℹ️ No document upload needed")
        
        # Final check after doc upload
        time.sleep(3)
        
        final_status = check_verification_status(page)
        if final_status.get('verified'):
            log("✅ VERIFICATION SUCCESSFUL! (Status verified)")
            log(f"🔗 {final_status.get('url', page.url)}")
            return {
                'success': True,
                'redirectUrl': final_status.get('url', page.url),
                'teacher': teacher_data
            }
        
        # Handle email verification flow
        if final_status.get('email_sent'):
            log("📧 Email verification sent - check inbox")
            return {
                'success': False,
                'pending': True,
                'email_sent': True,
                'message': final_status.get('message', 'Email verification sent'),
                'teacher': teacher_data
            }
        
        if final_status.get('error'):
            log(f"❌ {final_status.get('message', 'Verification failed')}")
            return {'success': False, 'rejected': True, 'message': final_status.get('message')}
        
        # Check for generic errors
        error_el = page.locator('[class*="error"]')
        if error_el.count() > 0:
            error_text = error_el.first.inner_text()[:100]
            log(f"❌ Error: {error_text}")
            return {'success': False, 'rejected': True, 'message': error_text}
        
        log("⏳ Verification not confirmed - check manually")
        return {'success': False, 'pending': True, 'message': 'Verification status unclear - please check manually'}
        
    except Exception as e:
        error_msg = str(e) or repr(e)
        tb = traceback.format_exc()
        log(f"❌ Error: {error_msg}")
        logger.error(f"Sync verification error: {tb}")
        return {'success': False, 'error': True, 'message': error_msg}
    
    finally:
        if keep_open:
            log("🔓 Browser staying open - press Enter to close...")
            input("\n>>> Press Enter to close browser <<<")
        if browser:
            browser.close()
        if pw:
            pw.stop()
