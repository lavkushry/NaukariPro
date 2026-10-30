import asyncio
from playwright.async_api import async_playwright

async def add_github():
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
        
        print("[*] Navigating to contact info overlay...")
        await page.goto("https://www.linkedin.com/in/lavkushry/overlay/contact-info/", wait_until="load", timeout=30000)
        await page.wait_for_timeout(3000)
        
        edit_btn = page.locator("a:has-text(\"Edit contact info\"), button:has-text(\"Edit contact info\"), [aria-label=\"Edit contact info\"]").first
        if await edit_btn.count() > 0:
            print("[+] Clicking Edit contact info...")
            await edit_btn.click()
            await page.wait_for_timeout(2500)
            
            add_web_btn = page.locator("button:has-text(\"Add website\")").first
            if await add_web_btn.count() > 0:
                print("[+] Clicking Add website...")
                await add_web_btn.click()
                await page.wait_for_timeout(1500)
                
                # Check for website url input
                url_inp = page.locator("input[placeholder*=\"https://\"], input[placeholder*=\"URL\"], input[placeholder*=\"Website\"][type=\"text\"]").last
                if await url_inp.count() == 0:
                    # Look for newly added empty text inputs
                    empty_inputs = page.locator("input[type=\"text\"]")
                    cnt = await empty_inputs.count()
                    for i in range(cnt):
                        inp = empty_inputs.nth(i)
                        v = await inp.input_value()
                        if not v and await inp.is_visible():
                            url_inp = inp
                            break
                            
                if await url_inp.count() > 0:
                    print("[+] Found website URL input, entering GitHub URL...")
                    await url_inp.click()
                    await url_inp.fill("https://github.com/lavkushry")
                    await page.wait_for_timeout(1000)
                    
                    # Check website type dropdown
                    selects = await page.locator("select:visible").all()
                    for sel in selects:
                        opts = await sel.inner_text()
                        if "Portfolio" in opts or "Other" in opts or "Personal" in opts:
                            print(f"[+] Setting website type on select...")
                            try:
                                await sel.select_option(label="Portfolio")
                            except Exception:
                                try:
                                    await sel.select_option(label="Other")
                                except Exception:
                                    pass
                            await page.wait_for_timeout(500)
                            
                    # Save
                    save_btn = page.locator("button:has-text(\"Save\")").first
                    if await save_btn.count() > 0:
                        print("[*] Saving contact info...")
                        await save_btn.click()
                        await page.wait_for_timeout(4000)
                        print("[✓] GitHub link successfully added to Contact Info!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(add_github())
