import asyncio
from playwright.async_api import async_playwright

SKILLS_TO_ADD = [
    "Azure Databricks",
    "Azure Data Factory",
    "Microsoft Azure",
    "Apache Spark",
    "Delta Lake"
]

async def update_azure_fundamentals():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        cookies = [
            {"name": "li_at", "value": "AQEDASFcjCIBxG5oAAABoDI_WRIAAAGhpP3V1lYAR2QIX4pez5UcMQl7d9v5I_7x_k1SzjhwsDdvknAoHMls5fWMdIw2oWS5R3i5sEJzo6RMaSxNlFufA0V-OMW8FpK75MWpUTK15vAisb76871TPcKt", "domain": ".linkedin.com", "path": "/"},
            {"name": "JSESSIONID", "value": "\"ajax:7525523478491085393\"", "domain": ".linkedin.com", "path": "/"}
        ]
        await context.add_cookies(cookies)
        page = await context.new_page()
        
        print("[*] Navigating to Azure Fundamentals edit form...")
        await page.goto("https://www.linkedin.com/in/lavkushry/details/certifications/edit/forms/35675840/", wait_until="load", timeout=30000)
        await page.wait_for_timeout(3000)
        
        # 1. Remove obsolete generic skills
        print("[*] Removing existing outline skills...")
        while True:
            rem = page.locator("button[aria-label*=\"Remove\"]").first
            if await rem.count() == 0:
                break
            aria = await rem.get_attribute("aria-label")
            print(f"  [-] Removing: {aria}")
            await rem.click()
            await page.wait_for_timeout(1200)
            
        # 2. Add high-value Data Engineering skills
        for skill in SKILLS_TO_ADD:
            print(f"[*] Adding skill: {skill}...")
            add_btn = page.locator("button:has-text(\"Add skill\")").first
            if await add_btn.count() > 0:
                await add_btn.click()
                await page.wait_for_timeout(1000)
                
            inp = page.locator("input[placeholder*=\"Skill (ex:\"]").first
            if await inp.count() > 0:
                await inp.click()
                await inp.fill(skill)
                await page.wait_for_timeout(1500)
                await page.keyboard.press("ArrowDown")
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(1500)
                print(f"  [+] Tagged: {skill}")
                
        # 3. Save certification
        save_btn = page.locator("button:has-text(\"Save\")").first
        if await save_btn.count() > 0:
            print("[*] Saving updated certification...")
            await save_btn.click()
            await page.wait_for_timeout(4000)
            print("[✓] Azure Fundamentals successfully updated with Data Engineering skills!")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(update_azure_fundamentals())
