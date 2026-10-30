import asyncio
from playwright.async_api import async_playwright

PROJECT_TITLE = "Real-Time Streaming Lakehouse Engine | Apache Kafka, PySpark, Delta Lake, Grafana"

PROJECT_DESC = """Designed and implemented a distributed streaming telemetry ingestion and real-time Lakehouse analytics platform processing 1.5M+ operational events/day across distributed microservices.

• Engineered stateful stream processing pipelines using PySpark Structured Streaming and Apache Kafka on Kubernetes, streaming high-velocity telemetry logs into Delta Lake with sub-second end-to-end latency.
• Automated schema evolution, bad-record quarantine handling, and real-time data quality validation gates, reducing pipeline data corruption and ingestion failure rates by 35%.
• Built analytical feature pipelines and real-time operational dashboards using Spark SQL, Delta Lake Gold layer aggregations, and Grafana, providing real-time SLA and throughput visibility for engineering teams.
• Provisioned reproducible distributed infrastructure and Kafka broker topics using Terraform, Helm charts, and ArgoCD GitOps pipelines."""

async def add_streaming_project():
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

        url = "https://www.linkedin.com/in/lavkushry/edit/forms/project/new/"
        print(f"[*] Navigating to new project form...")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # 1. Project Title
        title_inp = page.locator('input').first
        await title_inp.click()
        await title_inp.fill(PROJECT_TITLE)
        print("[+] Title entered.")

        # 2. Description
        desc_area = page.locator('textarea').first
        await desc_area.click()
        await desc_area.fill(PROJECT_DESC)
        print("[+] Description entered.")

        # 3. Dates: Start August (8) 2025, End March (3) 2026
        # Find selects
        selects = await page.locator('select').all()
        # Select 0: Start Month
        if len(selects) > 0:
            await selects[0].select_option(value="8")
            print("[+] Start Month set to August (8).")
        # Select 1: Start Year
        if len(selects) > 1:
            await selects[1].select_option(value="2025")
            print("[+] Start Year set to 2025.")
        # Select 2: End Month
        if len(selects) > 2:
            await selects[2].select_option(value="3")
            print("[+] End Month set to March (3).")
        # Select 3: End Year
        if len(selects) > 3:
            await selects[3].select_option(value="2026")
            print("[+] End Year set to 2026.")

        # 4. Associated with HFCL
        for s in selects:
            opts = await s.locator('option').all_inner_texts()
            for opt in opts:
                if 'HFCL' in opt:
                    await s.select_option(label=opt)
                    print(f"[+] Associated with set to '{opt}'.")
                    break

        await page.wait_for_timeout(1500)

        # 5. Save
        save_btn = page.locator('button:has-text("Save")')
        await save_btn.click()
        print("[+] Save button clicked. Waiting 5s...")
        await page.wait_for_timeout(5000)

        await browser.close()
        print("[✓] Real-Time Streaming Lakehouse Project successfully added!")

if __name__ == "__main__":
    asyncio.run(add_streaming_project())
