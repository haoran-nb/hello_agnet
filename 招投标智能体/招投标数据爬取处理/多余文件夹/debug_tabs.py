"""调试: 逐 Tab 点击后截图 + 打印 iframe 内容摘要"""
import asyncio
from playwright.async_api import async_playwright

URL = "https://ciac.zjw.sh.gov.cn/JGBAppZtbInterWeb/pc/#/jyggInfo?id=3013775&zbid=3002658&projectName=%E4%B8%AD%E5%9B%BD%E7%A7%91%E5%AD%A6%E9%99%A2%E4%B8%8A%E6%B5%B7%E5%BE%AE%E7%B3%BB%E7%BB%9F%E4%B8%8E%E4%BF%A1%E6%81%AF%E6%8A%80%E6%9C%AF%E7%A0%94%E7%A9%B6%E6%89%80%E6%96%B0%E5%BE%AE%E5%A4%A7%E5%8E%A6C%E5%BA%A7%E9%A1%B9%E7%9B%AE&gglx=zbjgggs&category"
TABS = ["招标公告", "补充公告", "中标候选人公示", "中标结果公告"]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto(URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        for tab in TABS:
            print(f"\n{'='*40}")
            print(f"TAB: {tab}")
            print(f"{'='*40}")

            els = await page.query_selector_all(f"text={tab}")
            if not els:
                print("  NOT FOUND")
                continue

            await els[0].click()
            await page.wait_for_timeout(3000)

            # 遍历所有 frame
            for i, frame in enumerate(page.frames):
                try:
                    html = await frame.content()
                    if len(html) < 200:
                        continue
                    text = await frame.evaluate("() => document.body ? document.body.innerText : ''")
                    if not text or len(text.strip()) < 30:
                        continue
                    print(f"\n  Frame {i}: {len(text)} chars")
                    print(f"  首200字: {text[:200]}")
                except Exception as e:
                    print(f"  Frame {i}: ERROR {e}")

        await browser.close()

asyncio.run(main())
