import asyncio
from playwright.async_api import async_playwright

PROJECT_TITLE = "Enterprise Medallion Lakehouse Platform | Azure Databricks, PySpark, Delta Lake, ADF"

PROJECT_DESC = """Architected and deployed an end-to-end Enterprise Medallion Lakehouse on Microsoft Azure and Databricks, orchestrating high-throughput ingestion and transformation of 2M+ daily operational events across Bronze (raw ingestion), Silver (curated/cleansed), and Gold (business analytics) Delta Lake tables.

• Engineered automated ETL/ELT pipelines using Azure Data Factory (ADF) and PySpark, orchestrating daily batch ingestion from heterogeneous relational backends and ADLS Gen2 storage containers into Delta Lake formats.
• Optimized PySpark distributed compute transformations using broadcast joins, Z-Ordering, and Delta Lake file compaction (OPTIMIZE/VACUUM), slashing query latency by 45% and reducing Databricks cluster compute spend by 30%.
• Implemented robust streaming ingestion using PySpark Structured Streaming and Apache Kafka with exactly-once checkpointing, sub-second latency, and automated dead-letter queue (DLQ) quarantine handling for malformed payloads.
• Configured fine-grained access governance using Unity Catalog and provisioned reusable Lakehouse infrastructure across dev/staging/prod environments via Terraform and GitHub Actions CI/CD workflows."""

async def update_lakehouse_project():
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

        url = "https://www.linkedin.com/in/lavkushry/details/projects/edit/forms/1876063683/"
        print(f"[*] Navigating to edit project 1876063683...")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # 1. Update Project Title
        title_inp = page.locator('input').first
        await title_inp.click()
        await title_inp.fill(PROJECT_TITLE)
        print("[+] Title updated.")

        # 2. Update Description
        desc_area = page.locator('textarea').first
        await desc_area.click()
        await desc_area.fill(PROJECT_DESC)
        print("[+] Description updated.")

        # 3. Check 'Currently working on this project' checkbox
        chk = page.locator('input[type="checkbox"]').first
        if await chk.count() > 0:
            await chk.evaluate('el => { if (!el.checked) { el.click(); el.dispatchEvent(new Event("change", {bubbles: true})); } }')
            print("[+] Checked 'Currently working on this project' via JS click.")

        # 4. Set Start Month & Year (October 2025)
        # Select 0: Month
        month_sel = page.locator('select').first
        if await month_sel.count() > 0:
            await month_sel.select_option(value="10")
            print("[+] Start Month set to October (10).")

        # Select 1: Year
        year_sel = page.locator('select').nth(1)
        if await year_sel.count() > 0:
            await year_sel.select_option(value="2025")
            print("[+] Start Year set to 2025.")

        # 5. Set 'Associated with' to CGI
        # Look for select containing 'CGI'
        selects = await page.locator('select').all()
        for s in selects:
            opts = await s.locator('option').all_inner_texts()
            for opt in opts:
                if 'CGI' in opt:
                    await s.select_option(label=opt)
                    print(f"[+] Associated with set to '{opt}'.")
                    break

        await page.wait_for_timeout(1500)

        # 6. Save
        save_btn = page.locator('button:has-text("Save")')
        await save_btn.click()
        print("[+] Save button clicked. Waiting 5s...")
        await page.wait_for_timeout(5000)

        await browser.close()
        print("[✓] Project 1876063683 successfully transformed into Enterprise Medallion Lakehouse Platform!")

if __name__ == "__main__":
    asyncio.run(update_lakehouse_project())
