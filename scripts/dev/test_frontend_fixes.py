import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from auth import PUBLIC_SIGNUP_ROLES, VALID_ROLES
from playwright.async_api import async_playwright

def test_server_admin_signup_rejection():
    """Test that PUBLIC_SIGNUP_ROLES only contains lawyer and company, and admin is not in public signup roles."""
    assert "admin" not in PUBLIC_SIGNUP_ROLES, f"admin must not be in PUBLIC_SIGNUP_ROLES: {PUBLIC_SIGNUP_ROLES}"
    assert "lawyer" in PUBLIC_SIGNUP_ROLES and "company" in PUBLIC_SIGNUP_ROLES, f"Public roles missing: {PUBLIC_SIGNUP_ROLES}"
    assert len(PUBLIC_SIGNUP_ROLES) == 2, f"Expected exactly 2 public roles, got: {PUBLIC_SIGNUP_ROLES}"
    print(f"[OK] Server-side PUBLIC_SIGNUP_ROLES correctly configured: {PUBLIC_SIGNUP_ROLES}")

async def run_verification():
    # 1. Run server-side unit verification
    test_server_admin_signup_rejection()

    # 2. Run Playwright browser end-to-end verification
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(channel="msedge", headless=True)
        except Exception:
            browser = await p.chromium.launch(channel="chrome", headless=True)

        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        out_dir = r"C:\Users\Devanandh\.gemini\antigravity-ide\brain\77885951-c9f9-4cea-988b-04a5847ca8fb\scratch"
        os.makedirs(out_dir, exist_ok=True)

        print("\n=== 1. Testing Auth Page (FIX 1 & FIX 2) ===")
        await page.goto("http://localhost:8080/auth.html", wait_until="networkidle")

        # Fix 1: Verify signup role dropdown options
        role_options = await page.eval_on_selector_all(
            "#signupRole option",
            "opts => opts.map(o => ({ value: o.value, text: o.textContent.trim() }))"
        )
        print("Signup role options in UI:", role_options)
        option_values = [o["value"] for o in role_options]
        assert "admin" not in option_values, f"Admin role must NOT be present in signup dropdown: {option_values}"
        assert "lawyer" in option_values and "company" in option_values, "Public roles (lawyer, company) missing"
        print("[OK] FIX 1: Signup dropdown only offers public roles ('lawyer', 'company'). 'admin' removed.")

        # Fix 2: Verify back link text
        back_link = await page.query_selector('.auth-back-link')
        assert back_link is not None, "Auth back link missing"
        back_link_text = (await back_link.inner_text()).strip()
        print(f"Auth back link text: {back_link_text.encode('ascii', 'replace').decode('ascii')}")
        assert "return to home" in back_link_text.lower(), f"Expected 'Return to Home', got: {back_link_text}"
        assert "dispute dashboard" not in back_link_text.lower(), f"Outdated 'Dispute Dashboard' text found: {back_link_text}"
        print("[OK] FIX 2: Auth back link correctly labeled 'Return to Home'")

        print("\n=== 2. Testing Dashboard Page (FIX 3) ===")
        # Seed authenticated session before navigating to dashboard
        await page.evaluate("""() => {
            sessionStorage.setItem("dss_token", "mock_token_123");
            sessionStorage.setItem("dss_jwt", "mock_token_123");
            sessionStorage.setItem("dss_user", JSON.stringify({ email: "counsel@lawfirm.in", role: "lawyer" }));
        }""")
        await page.goto("http://localhost:8080/dashboard.html", wait_until="networkidle")

        # Check Action Card 1: Launch Analysis Engine -> /index.html
        launch_btn = await page.query_selector('.action-card a.submit-btn')
        assert launch_btn is not None, "Launch Analysis Engine button missing"
        launch_href = await launch_btn.get_attribute("href")
        assert "index.html" in launch_href, f"Launch Analysis Engine should point to index.html, got: {launch_href}"
        print(f"[OK] Action Card 1 routes to case intake: {launch_href}")

        # Check Action Cards 2 & 3: Coming Soon disabled buttons
        action_cards = await page.query_selector_all('.dashboard-grid .card')
        assert len(action_cards) == 3, f"Expected 3 dashboard cards, got {len(action_cards)}"

        # Card 2 (Active Matter Registry)
        card2_btn = await action_cards[1].query_selector('button')
        assert card2_btn is not None, "Card 2 should have a disabled button"
        card2_disabled = await card2_btn.is_disabled()
        card2_text = (await card2_btn.inner_text()).strip()
        assert card2_disabled, "Card 2 button must be disabled"
        assert "coming soon" in card2_text.lower(), f"Expected 'Coming Soon', got: {card2_text}"
        print(f"[OK] FIX 3 Card 2 (Active Matter Registry): Disabled with text '{card2_text}'")

        # Card 3 (Find Legal Counsel)
        card3_btn = await action_cards[2].query_selector('button')
        assert card3_btn is not None, "Card 3 should have a disabled button"
        card3_disabled = await card3_btn.is_disabled()
        card3_text = (await card3_btn.inner_text()).strip()
        assert card3_disabled, "Card 3 button must be disabled"
        assert "coming soon" in card3_text.lower(), f"Expected 'Coming Soon', got: {card3_text}"
        print(f"[OK] FIX 3 Card 3 (Find Legal Counsel): Disabled with text '{card3_text}'")

        # Verify Sidebar Lawyer Finder doesn't point to case intake
        sidebar_lawyer_link = await page.query_selector('.sidebar-nav a[href*="lawyer-finder"]')
        if sidebar_lawyer_link:
            s_href = await sidebar_lawyer_link.get_attribute("href")
            assert "index.html" not in s_href, f"Sidebar lawyer finder should not link to index.html: {s_href}"
            print(f"[OK] FIX 3 Sidebar Lawyer Finder target is non-routing/placeholder: {s_href}")

        print("\n=== 3. Testing Case Intake Page (FIX 4 & Full Flow) ===")
        # Click Launch Analysis Engine
        await launch_btn.click()
        await page.wait_for_timeout(500)
        assert "index.html" in page.url, f"Expected to navigate to index.html, current URL: {page.url}"
        print("[OK] Successfully navigated from Dashboard to Case Intake")

        # Check Fix 4: Back to Dashboard button
        back_to_dash_btn = await page.query_selector('#backToDashboardBtn')
        assert back_to_dash_btn is not None, "#backToDashboardBtn missing in topbar"
        back_dash_text = (await back_to_dash_btn.inner_text()).strip()
        back_dash_href = await back_to_dash_btn.get_attribute("href")
        print(f"Back to dashboard button: text={back_dash_text.encode('ascii', 'replace').decode('ascii')}, href={repr(back_dash_href)}")
        assert "back to dashboard" in back_dash_text.lower(), f"Expected 'Back to Dashboard', got: {back_dash_text}"
        assert "dashboard.html" in back_dash_href, f"Expected link to dashboard.html, got: {back_dash_href}"
        print("[OK] FIX 4: Case Intake topbar has working 'Back to Dashboard' link")

        # Dismiss disclaimer modal if shown
        disclaimer_btn = await page.query_selector('#disclaimerAgreeBtn')
        if disclaimer_btn and await disclaimer_btn.is_visible():
            await disclaimer_btn.click()
            await page.wait_for_timeout(300)

        # Test clicking Back to Dashboard
        await back_to_dash_btn.click()
        await page.wait_for_timeout(500)
        assert "dashboard.html" in page.url, f"Expected to return to dashboard.html, current URL: {page.url}"
        print("[OK] Successfully navigated back from Case Intake to Dashboard!")

        # Take screenshots
        await page.screenshot(path=os.path.join(out_dir, "dashboard_verified.png"))
        await page.goto("http://localhost:8080/index.html", wait_until="networkidle")
        await page.screenshot(path=os.path.join(out_dir, "intake_verified.png"))
        await page.goto("http://localhost:8080/auth.html", wait_until="networkidle")
        await page.screenshot(path=os.path.join(out_dir, "auth_verified.png"))

        await browser.close()
        print("\nALL FIXES (1, 2, 3, 4) AND FULL FLOW VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_verification())

