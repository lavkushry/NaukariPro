import asyncio
import os
import sys
from playwright.async_api import async_playwright
from naukari_pro.modules.linkedin_session import LinkedInSessionManager
from naukari_pro.modules.linkedin_bot import LinkedInEasyApplyBot

async def main():
    print("Initializing session manager...", flush=True)
    mgr = LinkedInSessionManager()
    async with async_playwright() as p:
        ctx = await mgr.create_stealth_context(p, headless=True)
        try:
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            job_url = "https://www.linkedin.com/jobs/view/4480408392/"
            print(f"Navigating to {job_url}...", flush=True)
            await page.goto(job_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            bot = LinkedInEasyApplyBot(page=page)
            print("Calling execute_easy_apply...", flush=True)
            res = await bot.execute_easy_apply(
                page=page,
                job_info={"job_id": "4480408392", "title": "Data Engineer", "company": "Droisys", "url": job_url},
                dry_run=False,
                max_steps=12
            )
            print(f"FULL APPLY RESULT: {res}", flush=True)
            for h in bot.history:
                print(f"History: {h}", flush=True)
        except Exception as e:
            print(f"EXCEPTION: {type(e)} {e}", flush=True)
            import traceback
            traceback.print_exc()
        finally:
            await ctx.close()

if __name__ == "__main__":
    asyncio.run(main())
