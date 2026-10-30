import asyncio
from playwright.async_api import async_playwright

SWAPS = [
    {"del_id": "10", "del_name": "Cedar Policy Engine", "add_skill": "Delta Lake"},
    {"del_id": "16", "del_name": "python SDK", "add_skill": "Azure Data Factory"},
    {"del_id": "22", "del_name": "go sdk", "add_skill": "Apache Spark"},
    {"del_id": "38", "del_name": "Microsoft Copilot", "add_skill": "SQL"},
    {"del_id": "63", "del_name": "Celery", "add_skill": "Terraform"}
]

async def safe_goto(page, url, retries=3):
    for i in range(retries):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            return True
        except Exception as e:
            print(f"[!] Warning on goto ({url}): {e}. Retrying {i+1}/{retries} in 3s...")
            await asyncio.sleep(3)
    return False

async def update_skills():
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

        for item in SWAPS:
            del_id = item["del_id"]
            del_name = item["del_name"]
            add_skill = item["add_skill"]

            print(f"\n==========================================")
            print(f"[*] Processing: Delete '{del_name}' (ID: {del_id}) -> Add '{add_skill}'")
            print(f"==========================================")

            # 1. Delete
            del_url = f"https://www.linkedin.com/in/lavkushry/details/skills/edit/forms/{del_id}/"
            print(f"[*] Navigating to delete {del_name}...")
            ok = await safe_goto(page, del_url)
            if not ok:
                print(f"[-] Failed to navigate to {del_url}, skipping...")
                continue
            await page.wait_for_timeout(3000)

            del_btn = page.locator('button:has-text("Delete skill")').first
            if await del_btn.count() > 0:
                await del_btn.click()
                print(f"[+] Clicked Delete skill for {del_name}. Waiting for modal...")
                await page.wait_for_timeout(2000)

                # Look for confirmation modal button
                confirm_btn = page.locator('div[role="dialog"] button:has-text("Delete")')
                if await confirm_btn.count() > 0:
                    await confirm_btn.click()
                    print(f"[+] Clicked Confirm Delete modal button for {del_name}!")
                else:
                    any_del = page.locator('button:has-text("Delete")')
                    for b in await any_del.all():
                        txt = (await b.inner_text()).strip()
                        if txt == "Delete":
                            await b.click()
                            print(f"[+] Clicked Delete for {del_name}!")
                            break
                await page.wait_for_timeout(3000)
                print(f"[✓] Deletion of {del_name} completed.")
            else:
                print(f"[-] Delete skill button not found for {del_name} (may already be deleted).")

            # 2. Add
            add_url = "https://www.linkedin.com/in/lavkushry/skills/edit/forms/new/"
            print(f"[*] Navigating to Add Skill form for '{add_skill}'...")
            ok = await safe_goto(page, add_url)
            if not ok:
                print(f"[-] Failed to navigate to Add Skill form.")
                continue
            await page.wait_for_timeout(3000)

            inp = page.locator('input[placeholder*="Skill"]').first
            if await inp.count() > 0:
                await inp.click()
                await inp.fill(add_skill)
                await page.wait_for_timeout(1500)
                await page.keyboard.press("ArrowDown")
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(1000)

                save_btn = page.locator('button:has-text("Save")')
                if await save_btn.count() > 0:
                    await save_btn.click()
                    print(f"[+] Save clicked for '{add_skill}'. Waiting 4s...")
                    await page.wait_for_timeout(4000)
                    print(f"[✓] Added '{add_skill}' successfully!")
                else:
                    print(f"[-] Save button not found for '{add_skill}'.")
            else:
                print(f"[-] Skill input field not found.")

            await page.wait_for_timeout(2000)

        await browser.close()
        print("\n[✓] All skill updates completed successfully!")

if __name__ == "__main__":
    asyncio.run(update_skills())
