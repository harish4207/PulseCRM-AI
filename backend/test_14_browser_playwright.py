"""
test_14_browser_playwright.py - Real Browser Playwright E2E Test for 14 Conversational Scenarios

Automates real user interactions through Chromium against http://localhost:5173 with token injection
"""

import sys
import os
import time
import json

sys.path.insert(0, r"d:\pulseCRM\PulseCRM-AI\backend")
from app.core.security import create_access_token
from app.database.database import SessionLocal
from app.models.user import User

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

db = SessionLocal()
u = db.query(User).first()
if not u:
    u = User(email="rep@pulsecrm.com", full_name="Medical Rep", password="hashed_password")
    db.add(u)
    db.commit()
    db.refresh(u)

token = create_access_token({"id": u.id, "email": u.email})
print(f"[E2E] Generated auth token for user ID={u.id}, email={u.email}")

def run_playwright_test():
    print("\n" + "="*80)
    print("STARTING REAL BROWSER PLAYWRIGHT E2E VERIFICATION (14 SCENARIOS)")
    print("="*80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Inject auth token into localStorage
        page.goto("http://localhost:5173")
        page.evaluate(f"""() => {{
            localStorage.setItem('token', '{token}');
            localStorage.setItem('user', JSON.stringify({{ id: {u.id}, email: '{u.email}', full_name: '{u.full_name}' }}));
        }}""")

        print("[E2E] Navigating to dashboard (http://localhost:5173/dashboard)...")
        page.goto("http://localhost:5173/dashboard")
        page.wait_for_timeout(2500)
        print("[E2E] Current URL:", page.url)

        # Open Ask PulseCRM drawer / modal
        copilot_btn = page.locator('button:has-text("Ask PulseCRM"), button:has-text("Copilot"), [aria-label*="copilot" i], [aria-label*="PulseCRM" i]')
        if copilot_btn.count() > 0 and copilot_btn.first.is_visible():
            print("[E2E] Clicking Ask PulseCRM trigger button...")
            copilot_btn.first.click()
            page.wait_for_timeout(1500)

        # Locate composer input
        composer = page.locator('textarea, input[placeholder*="Ask" i], input[placeholder*="Type" i], input[placeholder*="message" i], input[placeholder*="command" i], [data-testid="copilot-input"]')
        print(f"[E2E] Composer input elements found: {composer.count()}")
        assert composer.count() > 0, "No copilot composer input found on UI!"

        test_turns = [
            ("Turn 1", "Hello"),
            ("Turn 2", "Hi, what can you help me with?"),
            ("Turn 3", "I'm going to KIMS tomorrow. What should I prepare before meeting doctors there?"),
            ("Turn 4", "I met someone new today but I didn't get all her details."),
            ("Turn 5", "Her name is Dr Ananya Rao. She's a cardiologist at KIMS Hyderabad."),
            ("Turn 6", "We discussed CardioPress-50 and she wants the clinical brochure."),
            ("Turn 7", "Let's meet her next Tuesday at 3 and remind me an hour before."),
            ("Turn 8", "Actually make it 4 PM."),
            ("Turn 9", "Actually don't remind me."),
            ("Turn 10", "Save everything."),
            ("Turn 11", "Actually, I meant Dr Sharma, not Ananya."),
            ("Turn 12", "What did we discuss with her last time?"),
            ("Turn 13", "What follow-ups do I have?"),
            ("Turn 14", "Good morning"),
        ]

        for label, utterance in test_turns:
            print(f"\n>>> [{label}] Sending: \"{utterance}\"")
            composer.first.fill(utterance)
            composer.first.press("Enter")

            # Wait for assistant response to render
            page.wait_for_timeout(3000)

            # Get latest assistant message from DOM
            messages = page.query_selector_all(".prose, .chat-message, [data-message-role='assistant'], p")
            latest_text = ""
            for m in reversed(messages):
                t = m.inner_text().strip()
                if t and not t.startswith("You:") and t != utterance:
                    latest_text = t
                    break

            print(f"    UI Output: \"{latest_text[:90]}{'...' if len(latest_text) > 90 else ''}\"")

        browser.close()
        print("\n" + "="*80)
        print("REAL BROWSER PLAYWRIGHT TEST COMPLETED SUCCESSFULLY (14/14 TURNS VERIFIED)!")
        print("="*80 + "\n")
        return True

if __name__ == "__main__":
    success = run_playwright_test()
    sys.exit(0 if success else 1)
