"""Connect to Edge via CDP and upload PDF to MinerU."""
import asyncio
import os
import json
import sys

async def main():
    from playwright.async_api import async_playwright

    pdf_path = r"C:\Users\Ran'lenovo\Desktop\互普\招投标agent知识库\闵行区华漕社区MHP0-1401单元28-01地块综合开发项目\中标候选人公示.pdf"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, "cdp_log.txt")

    def p(msg):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    # Clear log
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("")

    async with async_playwright() as pw:
        p("[1] Connecting to Edge via CDP...")
        browser = await pw.chromium.connect_over_cdp("http://localhost:9222")
        contexts = browser.contexts
        p(f"  Found {len(contexts)} contexts")

        # Get existing page or create new one
        if contexts:
            context = contexts[0]
            pages = context.pages
            p(f"  Found {len(pages)} pages")
            # Find mineru.net page
            page = None
            for pg in pages:
                if "mineru" in pg.url:
                    page = pg
                    break
            if not page:
                page = await context.new_page()
                await page.goto("https://mineru.net", wait_until="networkidle", timeout=30000)
        else:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://mineru.net", wait_until="networkidle", timeout=30000)

        p(f"  Current URL: {page.url}")
        p(f"  Title: {await page.title()}")

        # Take screenshot to see current state
        ss_path = os.path.join(base_dir, "mineru_page.png")
        await page.screenshot(path=ss_path, full_page=False)
        p(f"  Screenshot saved: {ss_path}")

        # Look for file upload input or drag-drop area
        p("[2] Looking for upload elements...")
        upload_inputs = await page.query_selector_all("input[type='file']")
        p(f"  Found {len(upload_inputs)} file inputs")

        # Check all input elements
        all_inputs = await page.query_selector_all("input")
        for inp in all_inputs:
            inp_type = await inp.get_attribute("type") or ""
            inp_name = await inp.get_attribute("name") or ""
            inp_accept = await inp.get_attribute("accept") or ""
            p(f"  Input: type={inp_type} name={inp_name} accept={inp_accept}")

        # Look for upload button or area
        buttons = await page.query_selector_all("button")
        for btn in buttons:
            text = await btn.inner_text()
            if text.strip():
                p(f"  Button: '{text.strip()[:50]}'")

        # Look for any element with upload-related text
        upload_area = await page.query_selector("[class*='upload'], [class*='drop'], [class*='drag']")
        if upload_area:
            tag = await upload_area.evaluate("el => el.tagName")
            cls = await upload_area.get_attribute("class") or ""
            p(f"  Upload area: <{tag}> class='{cls[:80]}'")

        p("[3] Done scanning. Check cdp_log.txt and mineru_page.png")

asyncio.run(main())
