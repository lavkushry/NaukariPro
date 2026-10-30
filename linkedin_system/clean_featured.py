import asyncio
from playwright.async_api import async_playwright

async def clean_featured():
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

        print("[*] Navigating to Featured details page...")
        await page.goto("https://www.linkedin.com/in/lavkushry/details/featured/", wait_until="load", timeout=30000)
        await page.wait_for_timeout(3000)

        # Look for 'Remove from featured' buttons
        rem_btns = page.locator('button:has-text("Remove from featured")')
        count = await rem_btns.count()
        print(f"Found {count} 'Remove from featured' buttons.")

        # Loop until no more 'Remove from featured' buttons exist or max 6
        for i in range(count):
            btn = page.locator('button:has-text("Remove from featured")').first
            if await btn.count() > 0:
                await btn.click()
                print(f"  [+] Clicked 'Remove from featured' #{i+1}")
                await page.wait_for_timeout(2000)

                # Check if there is a confirmation modal
                confirm = page.locator('div[role="dialog"] button:has-text("Remove")')
                if await confirm.count() > 0:
                    await confirm.click()
                    print(f"  [+] Confirmed removal #{i+1}")
                    await page.wait_for_timeout(2000)

        await page.wait_for_timeout(2000)
        await browser.close()
        print("[✓] Featured cleanup complete!")

if __name__ == "__main__":
    asyncio.run(clean_featured())
