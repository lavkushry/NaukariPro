import asyncio
from playwright.async_api import async_playwright

SKILLS_TO_ADD = [
    "Azure Databricks",
    "Delta Lake",
    "PySpark",
    "Apache Spark"
]

async def add_databricks_cert():
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
        
        print("[*] Navigating to Add Certification form...")
        await page.goto("https://www.linkedin.com/in/lavkushry/details/certifications/edit/forms/new/?profileFormEntryPoint=Detail", wait_until="load", timeout=30000)
        await page.wait_for_timeout(3000)
        
        # 1. Fill Name
        name_input = page.locator("input[placeholder*=\"Ex: Microsoft certified\"]").first
        await name_input.click()
        await name_input.fill("Databricks Accredited Lakehouse Fundamentals")
        await page.wait_for_timeout(1000)
        print("[+] Entered Name: Databricks Accredited Lakehouse Fundamentals")
        
        # 2. Fill Issuing Organization
        org_input = page.locator("input[placeholder*=\"Ex: Microsoft\"]").first
        await org_input.click()
        await org_input.fill("Databricks")
        await page.wait_for_timeout(1500)
        await page.keyboard.press("ArrowDown")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1000)
        print("[+] Selected Organization: Databricks")
        
        # 3. Issue Date (Month / Year)
        selects = await page.locator("select").all()
        print(f"[*] Found {len(selects)} select dropdowns.")
        if len(selects) >= 2:
            # First select is issue month, second is issue year
            await selects[0].select_option(label="October")
            await page.wait_for_timeout(500)
            await selects[1].select_option(label="2025")
            await page.wait_for_timeout(500)
            print("[+] Selected Issue Date: October 2025")
            
        # 4. Add Skills
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
                
        # 5. Save Certification
        save_btn = page.locator("button:has-text(\"Save\")").first
        if await save_btn.count() > 0:
            print("[*] Saving new certification...")
            await save_btn.click()
            await page.wait_for_timeout(4000)
            print("[✓] Databricks Accredited Lakehouse Fundamentals successfully added!")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(add_databricks_cert())
