import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        # Try launching with msedge or chrome channel
        try:
            browser = await p.chromium.launch(channel="msedge", headless=True)
        except Exception:
            browser = await p.chromium.launch(channel="chrome", headless=True)
            
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://localhost:8080/landing.html", wait_until="networkidle")
        
        out_dir = r"C:\Users\Devanandh\.gemini\antigravity-ide\brain\77885951-c9f9-4cea-988b-04a5847ca8fb\scratch"
        os.makedirs(out_dir, exist_ok=True)
        screenshot_path = os.path.join(out_dir, "landing_hero_1440.png")
        
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"Screenshot saved to: {screenshot_path}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
