"""
网易云音乐评论区爬虫 — Playwright 异步版

策略：
  网易云歌曲页(SAP)通过 iframe 加载评论区。爬虫进入 iframe 后直接解析
  DOM 提取评论。评论区结构:
    div.cmmts > div.itm         每条评论
      div.cnt.f-brk > a.s-fc7   用户名
      div.cnt.f-brk              内容 (文本)
      a[data-type="like"]        点赞
      div.time.s-fc4             时间
    div.m-page a                 分页按钮

用法:
  python netease_comment_spider.py --song-id <歌曲ID>
  python netease_comment_spider.py --song-id 186016         # 周杰伦《晴天》
  python netease_comment_spider.py --song-id 431796         # 陈奕迅《十年》
  python netease_comment_spider.py --song-id 436514312      # 赵雷《成都》
  python netease_comment_spider.py --song-id 186016 --pages 3  # 翻3页
"""

import asyncio
import json
import csv
import re
import time
import argparse
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PwTimeout


# ================================================================
#  配置
# ================================================================

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ================================================================
#  辅助
# ================================================================

def parse_likes(text: str) -> int:
    """(82.3万) -> 823000,  (37) -> 37"""
    if not text:
        return 0
    text = text.strip().strip("()").replace(",", "")
    if "万" in text:
        try:
            return int(float(text.replace("万", "")) * 10000)
        except ValueError:
            return 0
    try:
        return int(text)
    except ValueError:
        return 0


# ================================================================
#  核心
# ================================================================

EXTRACT_JS = """
() => {
    const items = document.querySelectorAll('div.cmmts div.itm');
    const results = [];
    const seen = new Set();
    for (const item of items) {
        try {
            const cid = item.getAttribute('data-id') || '';
            const userEl = item.querySelector('div.cnt.f-brk a.s-fc7');
            const userName = userEl ? userEl.innerText.trim() : '匿名';
            const href = userEl ? (userEl.getAttribute('href') || '') : '';
            const uidMatch = href.match(/id=(\\d+)/);
            const uid = uidMatch ? uidMatch[1] : '';
            const cntEl = item.querySelector('div.cnt.f-brk');
            const full = cntEl ? cntEl.innerText.trim() : '';
            const content = userName && full.startsWith(userName)
                ? full.substring(userName.length).trim() : full;
            const likeEl = item.querySelector('a[data-type="like"]');
            const likesText = likeEl ? likeEl.innerText.trim() : '0';
            const timeEl = item.querySelector('div.time.s-fc4');
            const timeStr = timeEl ? timeEl.innerText.trim() : '';
            const key = cid || uid + '|' + content.substring(0, 30);
            if (!seen.has(key)) { seen.add(key);
                results.push({ comment_id: cid, user_name: userName,
                    user_id: uid, content, likes_text: likesText, time_str: timeStr }); }
        } catch(e) {}
    }
    return results;
}
"""


async def scrape_song_comments(
    song_id: int,
    max_pages: int = 5,
    headless: bool = True,
) -> list[dict]:
    all_comments = []
    seen = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(
            user_agent=USER_AGENT, viewport={"width": 1400, "height": 900}, locale="zh-CN",
        )
        page = await ctx.new_page()

        print(f"[网易云] 打开页面: song?id={song_id}")
        await page.goto(
            f"https://music.163.com/#/song?id={song_id}",
            wait_until="domcontentloaded", timeout=45000,
        )

        # 等 iframe
        target = None
        for _ in range(20):
            await page.wait_for_timeout(300)
            for f in page.frames:
                if "/song?id=" in f.url and "/#/" not in f.url:
                    target = f
                    break
            if target:
                break

        if not target:
            print("[FAIL] iframe 未找到")
            await browser.close()
            return []

        # 评论区可能隐藏 (f-hide)
        try:
            await target.wait_for_selector("div.cmmts", state="attached", timeout=15000)
        except PwTimeout:
            print("[FAIL] 评论区未加载")
            await browser.close()
            return []

        # 尝试切到"最新评论"（如果评论区含 tab）
        try:
            sub_tabs = await target.query_selector_all("div.cmmts .u-tab a")
            for tb in sub_tabs:
                tb_txt = (await tb.inner_text()).strip()
                if "最新" in tb_txt:
                    await tb.click()
                    await page.wait_for_timeout(1500)
                    print("[OK] 切换到 最新评论")
                    break
        except Exception:
            pass

        # ===== 翻页抓取 =====
        for pg in range(1, max_pages + 1):
            raw = await target.evaluate(EXTRACT_JS)
            page_items = []
            for r in raw:
                dedup = r["comment_id"] or f'{r["user_id"]}|{r["content"][:30]}'
                if dedup not in seen:
                    seen.add(dedup)
                    page_items.append({
                        "comment_id": r["comment_id"],
                        "user_name": r["user_name"],
                        "user_id": r["user_id"],
                        "content": r["content"],
                        "likes": parse_likes(r["likes_text"]),
                        "time_str": r["time_str"],
                    })
            all_comments.extend(page_items)
            print(f"  第 {pg} 页: {len(page_items)} 条 (累计 {len(all_comments)})")

            if pg >= max_pages:
                break

            # 找下一页
            next_btn = None
            try:
                links = await target.query_selector_all("div.m-page a")
                for link in links:
                    txt = (await link.inner_text()).strip()
                    cls = (await link.get_attribute("class")) or ""
                    if txt in [">", "›"] and "js_disabled" not in cls:
                        next_btn = link
                        break
            except Exception:
                pass

            if not next_btn:
                print("  [停止] 没有更多页")
                break

            try:
                async with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                    await next_btn.click()
            except Exception:
                try:
                    await next_btn.click()
                    await page.wait_for_timeout(2000)
                except Exception as e:
                    print(f"  翻页失败: {e}")
                    break

            # 翻页后重新等评论区
            try:
                await target.wait_for_selector("div.cmmts", state="attached", timeout=10000)
            except PwTimeout:
                print("  [停止] 翻页后评论区未出现")
                break

        await browser.close()

    return all_comments


# ================================================================
#  保存
# ================================================================

def save_json(comments, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)
    print(f"[SAVE] JSON -> {path} ({len(comments)} 条)")


def save_csv(comments, path):
    if not comments:
        return
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=comments[0].keys())
        w.writeheader()
        w.writerows(comments)
    print(f"[SAVE] CSV -> {path} ({len(comments)} 条)")


# ================================================================
#  CLI
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="网易云音乐评论区爬虫 (Playwright)")
    parser.add_argument("--song-id", type=int, required=True, help="歌曲 ID")
    parser.add_argument("--pages", type=int, default=1, help="翻页数 (默认 1)")
    parser.add_argument("-o", "--output", type=str, default="", help="输出路径 (.json / .csv)")
    parser.add_argument("--no-headless", action="store_true", help="显示浏览器")

    args = parser.parse_args()
    out = Path(args.output) if args.output else Path(f"comments_{args.song_id}.json")

    t0 = time.time()
    comments = asyncio.run(
        scrape_song_comments(
            song_id=args.song_id,
            max_pages=args.pages,
            headless=not args.no_headless,
        )
    )
    elapsed = time.time() - t0

    if comments:
        print(f"\n[DONE] 共 {len(comments)} 条, 耗时 {elapsed:.1f}s")
        if out.suffix == ".csv":
            save_csv(comments, str(out))
        else:
            save_json(comments, str(out))
        print("\n--- 前 3 条 ---")
        for i, c in enumerate(comments[:3], 1):
            print(f"  {i}. {c['user_name']}: {c['content'][:60]}... [{c['likes']}赞]")
    else:
        print(f"\n[FAIL] 未抓到评论 (耗时 {elapsed:.1f}s)")


if __name__ == "__main__":
    main()
