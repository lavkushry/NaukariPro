import asyncio
from playwright.async_api import async_playwright

JOB_TITLES = "Azure Data Engineer, Data Engineer, Big Data Engineer, Cloud Data Engineer, MLOps Engineer"

LOCATIONS_TO_ADD = [
    "Bengaluru, Karnataka, India",
    "Hyderabad, Telangana, India"
]

LOCATIONS_TO_REMOVE = [
    "Berlin",
    "Amsterdam"
]

async def update_job_preferences():
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

        print("[*] Navigating to SEEKING_PREFERENCES...")
        await page.goto('https://www.linkedin.com/jobs/preferences/?viewType=SEEKING_PREFERENCES', wait_until='load', timeout=30000)
        await page.wait_for_timeout(3000)

        # 1. Open Job Preferences dialog
        otw_btn = page.locator('div[role="button"]:has-text("Open to work")').first
        await otw_btn.click()
        await page.wait_for_timeout(2500)
        print("[+] Opened Job Preferences dialog.")

        # 2. Update Job Titles in textbox
        title_box = page.locator('div[role="textbox"][contenteditable="true"]').first
        if await title_box.count() > 0:
            print("[*] Updating job titles textbox...")
            await title_box.click()
            await page.keyboard.press("Meta+A")
            await page.keyboard.press("Backspace")
            await title_box.fill(JOB_TITLES)
            await page.wait_for_timeout(1000)
            print(f"[+] Entered Job Titles: '{JOB_TITLES}'")

        # 3. Open Location Preferences dialog
        loc_btn = page.locator('[aria-label="Edit location preferences"]').first
        if await loc_btn.count() > 0:
            print("[*] Opening Location preferences...")
            await loc_btn.click()
            await page.wait_for_timeout(2500)

            # 3a. Remove unwanted locations
            for rem in LOCATIONS_TO_REMOVE:
                lbl = page.locator(f'label:has-text("{rem}")').first
                if await lbl.count() > 0:
                    await lbl.click()
                    print(f"  [-] Removed location: {rem}")
                    await page.wait_for_timeout(1000)

            # 3b. Add Indian tech hub locations
            for loc in LOCATIONS_TO_ADD:
                add_loc_btn = page.locator('button:has-text("Add location")').first
                if await add_loc_btn.count() > 0:
                    await add_loc_btn.click()
                    await page.wait_for_timeout(1000)

                inp = page.locator('input[placeholder*="Add location"]').first
                if await inp.count() > 0:
                    await inp.click()
                    await inp.fill(loc)
                    await page.wait_for_timeout(1500)
                    await page.keyboard.press("ArrowDown")
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(1000)
                    print(f"  [+] Added location: '{loc}'")

            # 3c. Save Location dialog
            loc_save = page.locator('button:has-text("Save")').last
            await loc_save.click()
            print("[+] Saved location preferences. Waiting 3s...")
            await page.wait_for_timeout(3000)

        # 4. Save Main Job Preferences dialog
        main_save = page.locator('button:has-text("Save")').first
        if await main_save.count() > 0:
            await main_save.click()
            print("[+] Saved main Job Preferences! Waiting 4s...")
            await page.wait_for_timeout(4000)

        await browser.close()
        print("\n[✓] Job Preferences and Recruiter Search Targeting successfully updated and saved live!")

if __name__ == "__main__":
    asyncio.run(update_job_preferences())
