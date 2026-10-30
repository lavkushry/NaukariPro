import asyncio
from playwright.async_api import async_playwright

LAKEHOUSE_SKILLS = ["Azure Databricks", "PySpark", "Delta Lake", "Azure Data Factory", "Apache Spark", "SQL"]
STREAMING_SKILLS = ["Apache Spark", "Apache Kafka", "PySpark", "Delta Lake", "SQL"]

OBSOLETE_TAGS = [
    "Remove Bootstrap (Framework) from list",
    "Remove React.js from list",
    "Remove HTML5 from list",
    "Remove Cascading Style Sheets (CSS) from list",
    "Remove JavaScript from list",
    "Remove Flask from list"
]

async def add_skill_to_form(page, skill_name):
    try:
        add_btn = page.locator('button:has-text("Add skill")').first
        if await add_btn.count() > 0:
            await add_btn.click()
            await page.wait_for_timeout(1000)

            inp = page.locator('input[placeholder*="Skill"]').first
            if await inp.count() > 0:
                await inp.click()
                await inp.fill(skill_name)
                await page.wait_for_timeout(1500)
                await page.keyboard.press("ArrowDown")
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(1000)
                print(f"  [+] Added skill to project: {skill_name}")
                return True
    except Exception as e:
        print(f"  [-] Failed to add skill '{skill_name}': {e}")
    return False

async def tune_skills():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800}
        )
        cookies = [
            {'name': 'li_at', 'value': 'AQEDASFcjCIBxG5oAAABoDI_WRIAAAGhpP3V1lYAR2QIX4pez5UcMQl7d9v5I_7x_k1SzjhwsDdvknAoHMls5fWMdIw2oWS5R3i5sEJzo6RMaSxNlFufA0V-OMW8FpK75MWpUTK15vAisb76871TPcKt', 'domain': '.linkedin.com', 'path': '/'},
            {'name': 'JSESSIONID', 'value': '\"ajax:7525523478491085393\"', 'domain': '.linkedin.com', 'path': '/'}
        ]
        await context.add_cookies(cookies)
        page = await context.new_page()

        # 1. Update Project 1876063683 (Enterprise Medallion Lakehouse)
        print("\n[*] Navigating to Enterprise Medallion Lakehouse form (1876063683)...")
        await page.goto("https://www.linkedin.com/in/lavkushry/details/projects/edit/forms/1876063683/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Remove obsolete tags
        for aria_label in OBSOLETE_TAGS:
            del_tag_btn = page.locator(f'button[aria-label="{aria_label}"]').first
            if await del_tag_btn.count() > 0:
                await del_tag_btn.click()
                print(f"  [-] Removed obsolete tag: {aria_label}")
                await page.wait_for_timeout(500)

        # Add Data Engineering skills
        for sk in LAKEHOUSE_SKILLS:
            await add_skill_to_form(page, sk)

        # Save
        save_btn = page.locator('button:has-text("Save")')
        await save_btn.click()
        print("[+] Save clicked on Project 1876063683. Waiting 4s...")
        await page.wait_for_timeout(4000)

        # 2. Update Project 18655427 (Real-Time Streaming Lakehouse)
        print("\n[*] Navigating to Real-Time Streaming Lakehouse form (18655427)...")
        await page.goto("https://www.linkedin.com/in/lavkushry/details/projects/edit/forms/18655427/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        for sk in STREAMING_SKILLS:
            await add_skill_to_form(page, sk)

        # Save
        save_btn = page.locator('button:has-text("Save")')
        await save_btn.click()
        print("[+] Save clicked on Project 18655427. Waiting 4s...")
        await page.wait_for_timeout(4000)

        await browser.close()
        print("\n[✓] Project skills successfully tuned and saved live!")

if __name__ == "__main__":
    asyncio.run(tune_skills())
