# -*- coding: utf-8 -*-
"""全自动调用 MinerU API 解析 PDF 并下载 Markdown 结果。"""
import os
import sys
import time
import json
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = r"D:\互普\招投标agent知识库\闵行区华漕社区MHP0-1401单元28-01地块综合开发项目\中标候选人公示.pdf"
FILE_NAME = "中标候选人公示.pdf"
OUTPUT_MD = os.path.join(BASE_DIR, "中标候选人公示.md")

API_BASE = "https://mineru.net/api/v1/agent"


def main():
    # ========== 第一步：获取 task_id 和上传 URL ==========
    print("[1/4] 请求 task_id 和 file_url...")
    resp = requests.post(
        f"{API_BASE}/parse/file",
        json={"file_name": FILE_NAME, "enable_table": True},
        timeout=30,
    )
    resp.raise_for_status()
    rj = resp.json()
    inner = rj.get("data", {})
    task_id = inner.get("task_id")
    file_url = inner.get("file_url")
    if not task_id or not file_url:
        print(f"[FAIL] 响应: {json.dumps(rj, ensure_ascii=False)}")
        return
    print(f"  task_id: {task_id}")

    # ========== 第二步：上传文件（不设 Content-Type，保留 OSS 签名） ==========
    print("[2/4] 上传 PDF 文件到 OSS...")
    file_size = os.path.getsize(PDF_PATH)
    print(f"  文件大小: {file_size / 1024:.1f} KB")
    with open(PDF_PATH, "rb") as f:
        put_resp = requests.put(file_url, data=f, timeout=120, verify=False)
    print(f"  状态码: {put_resp.status_code}")
    if put_resp.status_code != 200:
        print(f"  [FAIL] 上传失败: {put_resp.text[:300]}")
        return

    # ========== 第三步：轮询状态 ==========
    print("[3/4] 轮询解析状态...")
    poll_url = f"{API_BASE}/parse/{task_id}"
    start = time.time()
    while True:
        time.sleep(5)
        poll_resp = requests.get(poll_url, timeout=30, verify=False)
        poll_resp.raise_for_status()
        result = poll_resp.json()
        state = result.get("data", {}).get("state", "unknown")
        elapsed = time.time() - start
        print(f"  [{elapsed:.0f}s] state = {state}")

        if state == "done":
            print("  [OK] 解析完成!")
            break
        elif state in ("failed", "error"):
            print(f"  [FAIL] 解析失败: {json.dumps(result, ensure_ascii=False)}")
            return
        elif elapsed > 600:
            print("  [TIMEOUT] 超过10分钟，退出")
            return

    # ========== 第四步：下载 Markdown ==========
    result_data = result.get("data", {})
    markdown_url = result_data.get("markdown_url")
    if not markdown_url:
        for key in ("result", "data"):
            if isinstance(result_data.get(key), dict):
                markdown_url = result_data[key].get("markdown_url")
                if markdown_url:
                    break
    if not markdown_url:
        print(f"[FAIL] 未找到 markdown_url，响应: {json.dumps(result, ensure_ascii=False)}")
        return

    print(f"[4/4] 下载 Markdown...")
    print(f"  URL: {markdown_url[:120]}...")
    # Use curl to bypass Python ssl CA bundle issue on Windows
    import subprocess
    curl_proc = subprocess.run(
        ["curl", "-k", "-s", "-L", markdown_url],
        capture_output=True, timeout=60,
    )
    if curl_proc.returncode != 0:
        print(f"  [FAIL] curl failed: {curl_proc.stderr.decode('utf-8', errors='replace')[:300]}")
        return
    md_text = curl_proc.stdout.decode("utf-8")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(md_text)

    print(f"  [OK] 已保存: {OUTPUT_MD}")
    print(f"  文本长度: {len(md_text)} 字符")
    print("\n===== 全部完成 =====")


if __name__ == "__main__":
    main()
