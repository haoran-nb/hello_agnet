"""
中标候选人公示 PDF 提取器 v4
关键发现: PDF viewer 的真实 PDF 通过 /file/pdf/download 下载
"""

import asyncio
import os
import pdfplumber
from datetime import datetime
from playwright.async_api import async_playwright

PAGE_URL = "https://ciac.zjw.sh.gov.cn/JGBAppZtbInterWeb/pc/#/jyggInfo?id=3013842&zbid=3002168&projectName=%E8%88%AA%E5%A4%B4%E9%95%87%E6%96%87%E5%8C%96%E6%9C%8D%E5%8A%A1%E4%B8%AD%E5%BF%83%E4%BF%AE%E7%BC%AE%E5%B7%A5%E7%A8%8B%EF%BC%88%E4%BA%8C%E6%9C%9F%EF%BC%89&gglx=zbjgggs&category"
SAVE_DIR = r"D:\互普\招投标agent知识库\航头镇文化服务中心修缮工程（二期）"
PNAME = "航头镇文化服务中心修缮工程（二期）"
DATA_SRC = "**数据来源：** 上海市公共资源交易中心（https://ciac.zjw.sh.gov.cn）"


def tag_header(cat, name, url):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"<!--\n阶段: 招投标信息采集\n类别: {cat}\n项目名称: {name}\n地域: 上海市\n来源: {url}\n抓取日期: {ts}\n-->"


def save_md(tab, content, name, url):
    p = os.path.join(SAVE_DIR, f"{tab}.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"# {name}\n\n## {tab}\n\n{tag_header(tab, name, url)}\n\n---\n\n{content or '暂无内容'}\n\n---\n\n{DATA_SRC}\n")
    return p


def extract_pdf_tables(pdf_path):
    all_rows = []
    seen = set()
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or all(c is None or str(c).strip() == "" for c in row):
                        continue
                    cleaned = [str(c).strip() if c else "" for c in row]
                    key = tuple(cleaned)
                    if key not in seen:
                        seen.add(key)
                        all_rows.append(cleaned)
    return all_rows


def rows_to_markdown(rows):
    if not rows:
        return "暂无内容"
    max_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < max_cols:
            r.append("")
    non_empty = [ci for ci in range(max_cols) if any(rows[i][ci].strip() for i in range(len(rows)))]
    if not non_empty:
        return "暂无内容"
    filtered = [[r[ci] for ci in non_empty] for r in rows]
    header = filtered[0]
    body = filtered[1:]
    lines = ["| " + " | ".join(header) + " |"]
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


async def main():
    print("=" * 60)
    print(f"中标候选人公示 PDF 提取 v4: {PNAME}")
    print("=" * 60)

    os.makedirs(SAVE_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        # 只拦截 /file/pdf/download 请求
        pdf_downloads = []

        async def on_resp(resp):
            url = resp.url
            if "/file/pdf/download" in url:
                try:
                    body = await resp.body()
                    pdf_downloads.append({"url": url, "body": body, "size": len(body)})
                    print(f"  [拦截PDF下载] {len(body)} bytes")
                except Exception as e:
                    print(f"  [拦截失败] {e}")

        context.on("response", on_resp)

        page = await context.new_page()

        # Step 1: 导航
        print("\n[1] 导航...")
        try:
            await page.goto(PAGE_URL, wait_until="networkidle", timeout=30000)
        except Exception:
            pass
        await page.wait_for_timeout(3000)

        # Step 2: 点击中标候选人公示
        print("[2] 点击中标候选人公示...")
        els = await page.query_selector_all("text=中标候选人公示")
        if not els:
            print("  未找到")
            await browser.close()
            return
        await els[0].click()
        await page.wait_for_timeout(3000)

        # Step 3: 找 PDF viewer URL
        viewer_url = None
        for frame in page.frames:
            if frame.url and "pdfview" in frame.url.lower():
                viewer_url = frame.url
                print(f"[3] PDF viewer: {viewer_url[:80]}...")
                break

        if not viewer_url:
            print("[3] 未发现 PDF viewer")
            await browser.close()
            return

        # Step 4: 新标签页打开 PDF viewer
        print("[4] 打开 PDF viewer，等待下载...")
        pdf_page = await context.new_page()
        try:
            await pdf_page.goto(viewer_url, wait_until="networkidle", timeout=30000)
        except Exception:
            pass
        await pdf_page.wait_for_timeout(8000)

        await browser.close()

    # 处理结果
    if not pdf_downloads:
        print("\n[FAIL] 未拦截到 PDF 下载")
        return

    # 取最大的有效 PDF
    valid_pdfs = [d for d in pdf_downloads if d["size"] > 10000]  # 至少 10KB
    if not valid_pdfs:
        print("\n[FAIL] 没有足够大的 PDF")
        return

    best = max(valid_pdfs, key=lambda x: x["size"])
    pdf_path = os.path.join(SAVE_DIR, "中标候选人公示.pdf")
    with open(pdf_path, "wb") as f:
        f.write(best["body"])
    print(f"\n[5] PDF: {pdf_path} ({best['size']} bytes)")

    # 验证
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"  页数: {len(pdf.pages)}")
    except Exception as e:
        print(f"[FAIL] 无效 PDF: {e}")
        with open(pdf_path, "rb") as f:
            print(f"  文件头: {f.read(20)}")
        return

    # 解析
    print("[6] 解析...")
    rows = extract_pdf_tables(pdf_path)
    print(f"  {len(rows)} 行")

    md = rows_to_markdown(rows)
    md_path = save_md("中标候选人公示", md, PNAME, PAGE_URL)
    print(f"[7] MD: {md_path} ({len(md)} chars)")

    print(f"\n{'=' * 60}")
    print(md[:800])


if __name__ == "__main__":
    asyncio.run(main())
