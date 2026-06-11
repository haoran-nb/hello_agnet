"""
精准提取全部 6 个 Tab 的 iframe 原始数据
核心修复: 用 debug 脚本验证过的等待逻辑，确保数据值真正填充后再读取
"""

import asyncio
import os
import re
from datetime import datetime
from playwright.async_api import async_playwright

PAGE_URL = "https://ciac.zjw.sh.gov.cn/JGBAppZtbInterWeb/pc/#/jyggInfo?id=3013842&zbid=3002168&projectName=%E8%88%AA%E5%A4%B4%E9%95%87%E6%96%87%E5%8C%96%E6%9C%8D%E5%8A%A1%E4%B8%AD%E5%BF%83%E4%BF%AE%E7%BC%AE%E5%B7%A5%E7%A8%8B%EF%BC%88%E4%BA%8C%E6%9C%9F%EF%BC%89&gglx=zbjgggs&category"
SAVE_DIR = r"D:\互普\招投标agent知识库\航头镇文化服务中心修缮工程（二期）"
PNAME = "航头镇文化服务中心修缮工程（二期）"
DATA_SRC = "**数据来源：** 上海市公共资源交易中心（https://ciac.zjw.sh.gov.cn）"
TS = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

NAV_KEYWORDS = [
    "已完成", "未完成", "选中环节",
    "招标计划", "招标公告", "补充公告", "澄清公告",
    "中标候选人公示", "中标结果公告", "合同公示",
    "合同信息公开", "终止公告", "投诉处理结果公开"
]

# 只抓这 4 个 HTML 模式的 Tab（中标候选人公示是 PDF，澄清公告单独处理）
HTML_TABS = ["招标计划", "招标公告", "补充公告"]


def tag(cat):
    return f"<!--\n阶段: 招投标信息采集\n类别: {cat}\n项目名称: {PNAME}\n地域: 上海市\n来源: {PAGE_URL}\n抓取日期: {TS}\n-->"


def save_raw(filename, content):
    """保存原始抓取数据"""
    p = os.path.join(SAVE_DIR, filename)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return p


async def extract_content_frame_text(page):
    """从内容框架提取文本，跳过导航框架，等待数据填充"""
    for frame in page.frames:
        try:
            html = await frame.content()
            if len(html) < 200:
                continue
            text = await frame.evaluate("() => document.body ? document.body.innerText : ''")
            if not text or len(text.strip()) < 30:
                continue
            nav = sum(1 for kw in NAV_KEYWORDS if kw in text)
            if nav >= 5:
                continue
            return text.strip()
        except Exception:
            pass
    return ""


async def wait_for_real_data(page, min_filled_lines=3, timeout=15):
    """等待 iframe 中表格数据真正填充（至少 N 行有值）"""
    for _ in range(timeout * 2):
        await page.wait_for_timeout(500)
        text = await extract_content_frame_text(page)
        if not text:
            continue
        # 统计有值的行（tab 分隔且第二列非空）
        lines = text.split('\n')
        filled = 0
        for line in lines:
            if '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 2 and parts[1].strip():
                    filled += 1
        if filled >= min_filled_lines:
            return text
    return None


async def main():
    print("=" * 60)
    print(f"精准提取全部 Tab: {PNAME}")
    print("=" * 60)

    os.makedirs(SAVE_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        print("\n[1] 导航...")
        try:
            await page.goto(PAGE_URL, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"  超时: {e}")
        await page.wait_for_timeout(3000)

        # 先读取默认 Tab 的内容
        initial_text = await extract_content_frame_text(page)

        print("\n[2] 逐 Tab 提取...")
        results = {}

        for tab_name in HTML_TABS:
            print(f"\n  --- {tab_name} ---")
            try:
                els = await page.query_selector_all(f"text={tab_name}")
                if not els:
                    print(f"  [SKIP] 未找到")
                    continue

                # 点击
                await els[0].click()
                print(f"  [CLICK]，等待数据填充...")

                # 等待真实数据
                content = await wait_for_real_data(page, min_filled_lines=3, timeout=15)

                if content and content != initial_text:
                    results[tab_name] = content
                    f = save_raw(f"{tab_name}_raw.txt", content)
                    print(f"  [OK] {len(content)} chars -> {os.path.basename(f)}")
                else:
                    # 兜底: 再读一次
                    current = await extract_content_frame_text(page)
                    if current and current != initial_text:
                        results[tab_name] = current
                        f = save_raw(f"{tab_name}_raw.txt", current)
                        print(f"  [FALLBACK] {len(current)} chars -> {os.path.basename(f)}")
                    else:
                        results[tab_name] = ""
                        print(f"  [EMPTY] 无数据")
            except Exception as e:
                print(f"  [FAIL] {e}")
                results[tab_name] = ""

        await browser.close()

    # 输出汇总
    print(f"\n{'=' * 60}")
    print("提取结果汇总:")
    for name, content in results.items():
        filled = 0
        if content:
            for line in content.split('\n'):
                if '\t' in line:
                    parts = line.split('\t')
                    if len(parts) >= 2 and parts[1].strip():
                        filled += 1
        print(f"  {name}: {len(content)} chars, {filled} 行有值")
    print(f"{'=' * 60}")

    print(f"\n原始数据已保存到 {SAVE_DIR}")
    print("请检查 *_raw.txt 文件，确认数据完整性后再清洗为 v5 格式")


if __name__ == "__main__":
    asyncio.run(main())
