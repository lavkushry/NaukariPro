import asyncio
from playwright.async_api import async_playwright

async def capture_profile():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        cookies = [
            {"name": "li_at", "value": "AQEDASFcjCIBxG5oAAABoDI_WRIAAAGhpP3V1lYAR2QIX4pez5UcMQl7d9v5I_7x_k1SzjhwsDdvknAoHMls5fWMdIw2oWS5R3i5sEJzo6RMaSxNlFufA0V-OMW8FpK75MWpUTK15vAisb76871TPcKt", "domain": ".linkedin.com", "path": "/"},
            {"name": "JSESSIONID", "value": "\"ajax:7525523478491085393\"", "domain": ".linkedin.com", "path": "/"}
        ]
        await context.add_cookies(cookies)
        page = await context.new_page()
        print("[*] Navigating to profile...")
        await page.goto("https://www.linkedin.com/in/lavkushry/", wait_until="load", timeout=30000)
        await page.wait_for_timeout(3000)
        
        # Screenshot 1: Top profile view (Header, Headline, OTW, Analytics, About)
        await page.screenshot(path="linkedin_system/final_profile_top.png")
        print("[+] Captured final_profile_top.png")
        
        # Scroll down to experience
        await page.evaluate("window.scrollBy(0, 800)")
        await page.wait_for_timeout(1500)
        await page.screenshot(path="linkedin_system/final_profile_experience.png")
        print("[+] Captured final_profile_experience.png")
        
        # Scroll down to projects & certifications
        await page.evaluate("window.scrollBy(0, 900)")
        await page.wait_for_timeout(1500)
        await page.screenshot(path="linkedin_system/final_profile_projects_certs.png")
        print("[+] Captured final_profile_projects_certs.png")
        
        # Navigate to certifications details
        await page.goto("https://www.linkedin.com/in/lavkushry/details/certifications/", wait_until="load", timeout=30000)
        await page.wait_for_timeout(2500)
        await page.screenshot(path="linkedin_system/final_certifications.png")
        print("[+] Captured final_certifications.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_profile())
