"""K12 School Staff Scraper - Phased Version

Scrapes teacher info in phases to avoid timeout.

Usage:
    python -m k12.scraper.school_staff_scraper --phase 1
    python -m k12.scraper.school_staff_scraper --phase 2
    python -m k12.scraper.school_staff_scraper --all
"""

import json
import re
import time
import random
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import httpx
from playwright.sync_api import sync_playwright

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
SCRAPED_TEACHERS_FILE = DATA_DIR / "scraped_teachers.json"
PROGRESS_FILE = Path(__file__).parent / "scrape_progress.json"

# SheerID API
SHEERID_ORG_SEARCH = "https://orgsearch.sheerid.net/rest/organization/search"

# Schools by phase (2-3 schools each)
PHASE_SCHOOLS = {
    1: [
        {"name": "Bronx High School of Science", "url": "https://www.bxscience.edu/apps/staff/"},
        {"name": "Brooklyn Technical High School", "url": "https://www.bths.edu/apps/staff/"},
    ],
    2: [
        {"name": "Stuyvesant High School", "url": "https://stuy.enschool.org/apps/staff/"},
        {"name": "Lincoln High School Portland", "url": "https://www.pps.net/domain/110"},
    ],
    3: [
        {"name": "Academy Charter School", "url": "https://www.academycharterschool.org/staff"},
        {"name": "British School of Washington", "url": "https://www.britishschoolofwashington.org/staff"},
    ],
}


def verify_school_is_k12(school_name: str) -> Optional[Dict]:
    """Verify school exists in SheerID as K12 type."""
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(
                SHEERID_ORG_SEARCH,
                params={
                    "accountId": "5e5297c2dfc5fb00012e0f21",
                    "country": "US",
                    "type": "K12",
                    "name": school_name
                }
            )
            
            if response.status_code == 200:
                for school in response.json():
                    if school.get("type") == "K12":
                        return {
                            "id": school.get("id"),
                            "idExtended": str(school.get("id")),
                            "name": school.get("name"),
                            "city": school.get("city") or "Unknown",
                            "state": school.get("state") or "US",
                            "country": "US",
                            "type": "K12"
                        }
    except Exception as e:
        print(f"Error: {e}")
    return None


def scrape_staff_page(url: str) -> List[Dict]:
    """Scrape teacher emails from staff directory page."""
    teachers = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            
            html = page.content()
            
            # Extract emails
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = list(set(re.findall(email_pattern, html)))
            
            # Filter school emails
            school_emails = [e for e in emails if not any(x in e.lower() for x in 
                ['example', 'test', 'admin@', 'info@', 'office@', 'webmaster', 'noreply'])]
            
            for email in school_emails[:50]:
                name_parts = email.split('@')[0].replace('.', ' ').replace('_', ' ').split()
                if len(name_parts) >= 2:
                    teachers.append({
                        "first_name": name_parts[0].title(),
                        "last_name": name_parts[-1].title(),
                        "full_name": f"{name_parts[0].title()} {name_parts[-1].title()}",
                        "email": email.lower(),
                        "source_url": url
                    })
            
            browser.close()
            
    except Exception as e:
        print(f"Error scraping {url}: {e}")
    
    return teachers


def scrape_school(school_name: str, staff_url: str) -> Dict:
    """Scrape one school."""
    print(f"\n--- {school_name} ---")
    
    # Verify K12
    school_info = verify_school_is_k12(school_name)
    if not school_info:
        print(f"[X] Not found as K12")
        return {"error": "Not K12"}
    
    print(f"[OK] ID: {school_info['id']}")
    
    # Scrape
    teachers = scrape_staff_page(staff_url)
    print(f"[OK] {len(teachers)} teachers")
    
    # Enrich
    for t in teachers:
        t.update({
            "school_name": school_info["name"],
            "school_id": str(school_info["id"]),
            "school_city": school_info["city"],
            "school_state": school_info["state"],
            "position": "Teacher",
            "birth_date": f"198{random.randint(0,9)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "hire_date": f"20{random.randint(15,23)}-08-{random.randint(15,25):02d}",
        })
    
    return {"school": school_info, "teachers": teachers}


def load_progress() -> Dict:
    """Load scraping progress."""
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {"completed_phases": [], "total_teachers": 0}


def save_progress(progress: Dict):
    """Save progress."""
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


def load_existing_teachers() -> List[Dict]:
    """Load existing scraped teachers."""
    if SCRAPED_TEACHERS_FILE.exists():
        return json.loads(SCRAPED_TEACHERS_FILE.read_text(encoding="utf-8"))
    return []


def save_teachers(teachers: List[Dict]):
    """Save all teachers."""
    DATA_DIR.mkdir(exist_ok=True)
    with open(SCRAPED_TEACHERS_FILE, "w", encoding="utf-8") as f:
        json.dump(teachers, f, indent=2, ensure_ascii=False)


def run_phase(phase: int):
    """Run specific phase."""
    if phase not in PHASE_SCHOOLS:
        print(f"Invalid phase {phase}. Available: {list(PHASE_SCHOOLS.keys())}")
        return
    
    progress = load_progress()
    if phase in progress["completed_phases"]:
        print(f"Phase {phase} already completed. Skipping.")
        return
    
    print(f"\n{'='*40}")
    print(f"PHASE {phase} - {len(PHASE_SCHOOLS[phase])} schools")
    print(f"{'='*40}")
    
    all_teachers = load_existing_teachers()
    phase_teachers = []
    
    for school in PHASE_SCHOOLS[phase]:
        result = scrape_school(school["name"], school["url"])
        if "teachers" in result:
            phase_teachers.extend(result["teachers"])
        time.sleep(2)
    
    # Merge and save
    all_teachers.extend(phase_teachers)
    save_teachers(all_teachers)
    
    # Update progress
    progress["completed_phases"].append(phase)
    progress["total_teachers"] = len(all_teachers)
    save_progress(progress)
    
    print(f"\n[DONE] Phase {phase}: +{len(phase_teachers)} teachers")
    print(f"[TOTAL] {len(all_teachers)} teachers saved")


def run_all():
    """Run all phases."""
    for phase in sorted(PHASE_SCHOOLS.keys()):
        run_phase(phase)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=int, help="Phase number to run")
    parser.add_argument("--all", action="store_true", help="Run all phases")
    args = parser.parse_args()
    
    if args.all:
        run_all()
    elif args.phase:
        run_phase(args.phase)
    else:
        print("Usage: --phase N or --all")
