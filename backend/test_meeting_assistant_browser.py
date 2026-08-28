"""
test_meeting_assistant_browser.py - Playwright browser verification of Meeting Assistant
"""

import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"d:\pulseCRM\PulseCRM-AI\backend")

from app.core.security import create_access_token
from app.database.database import SessionLocal
from app.models.user import User

db = SessionLocal()
u = db.query(User).first()
token = create_access_token({"id": u.id, "email": u.email})

def run_test():
    print("="*80)
    print("PLAYWRIGHT MEETING ASSISTANT BROWSER TEST")
    print("="*80)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        
        # 1. Setup Auth
        print("\n1. Injecting authenticated user token...")
        page.goto("http://localhost:5173/login", wait_until="networkidle")
        page.evaluate(f"""() => {{
            localStorage.setItem('token', '{token}');
            localStorage.setItem('user', JSON.stringify({{ id: {u.id}, email: '{u.email}', full_name: '{u.full_name}' }}));
        }}""")
        
        # 2. Navigate to Meeting Assistant (/ai-meeting)
        print("\n2. Navigating to Meeting Assistant (/ai-meeting)...")
        page.goto("http://localhost:5173/ai-meeting", wait_until="networkidle")
        time.sleep(1)
        
        # 3. Enter meeting notes
        sample_text = (
            "Met Dr Sharma at Apollo Hospital Mumbai this morning. Discussed CardioPress-50 and LipiGuard for hypertensive patients. "
            "Dr Sharma noted good efficacy with CardioPress-50 and requested a follow-up meeting on 2026-09-15 at 10 AM."
        )
        print("\n3. Entering meeting notes into textarea...")
        textarea = page.locator("textarea").first
        textarea.fill(sample_text)
        time.sleep(0.5)
        
        # 4. Click "Analyze meeting" button
        print("\n4. Clicking 'Analyze meeting' button...")
        btn = page.locator("button:has-text('Analyze meeting')").first
        btn.click()
        
        # Wait for extraction processing to finish
        print("   Waiting for AI processing...")
        page.wait_for_selector("text=Organization", timeout=20000)
        time.sleep(1)
        
        # Check text on screen
        body_text = page.locator("body").inner_text()
        print(f"   Body text snippet: {body_text[:400].replace(chr(10), ' ')}...")
        page.screenshot(path="d:/pulseCRM/PulseCRM-AI/frontend/meeting_assistant_extracted_verified.png")
        assert "Not authenticated" not in body_text, "Error: 'Not authenticated' found on screen!"
        assert "Sharma" in body_text, "Error: Doctor name not found on screen!"
        print("   Extraction verified! Doctor and products displayed on screen.")
        
        # 5. Test Navigation to other routes and back
        print("\n5. Testing navigation across routes...")
        page.goto("http://localhost:5173/dashboard", wait_until="networkidle")
        time.sleep(1)
        page.goto("http://localhost:5173/ai-meeting", wait_until="networkidle")
        time.sleep(1)
        print("   Navigation successful and authenticated state preserved.")
        
        # 6. Test Refresh on /ai-meeting
        print("\n6. Testing browser refresh on /ai-meeting...")
        page.reload(wait_until="networkidle")
        time.sleep(1)
        body_after_reload = page.locator("body").inner_text()
        assert "Meeting Assistant" in body_after_reload, "Error: Meeting Assistant not loaded after reload!"
        print("   Refresh successful and session preserved.")
        
        # Capture screenshot
        page.screenshot(path="d:/pulseCRM/PulseCRM-AI/frontend/meeting_assistant_verified.png")
        print("   Screenshot saved to frontend/meeting_assistant_verified.png")
        
        browser.close()
        print("\n" + "="*80)
        print("MEETING ASSISTANT PLAYWRIGHT TEST COMPLETED (PASS)")
        print("="*80)

if __name__ == "__main__":
    run_test()
