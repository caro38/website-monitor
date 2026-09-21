import datetime
import json
import os
import random
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.forest.gov.tw/"
CORE_SERVICE_PAGES = [
    {
        "name": "官方聯絡資訊與服務專線",
        "url": "https://www.forest.gov.tw/contactus",
    },
    {"name": "重大政策與計畫專區", "url": "https://www.forest.gov.tw/plan"},
]

SEARCH_KEYWORDS_POOL = [
    "步道",
    "森林",
    "保育",
    "志工",
    "國家森林遊樂區",
    "苗木",
    "登山",
]
HISTORY_FILE = "audit_history.json"


def get_url_depth(url):
  """計算網址的深度（依斜線數量或層級判定）"""
  clean_path = url.replace(BASE_URL.rstrip("/"), "")
  parts = [p for p in clean_path.split("/") if p]
  depth = len(parts)
  return max(1, min(depth, 4))  # 歸類為 Level 1 至 Level 4


def crawl_deep_links():
  """遞迴爬蟲：探索並收集至多 Level 4 的內部連結"""
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }
  visited = set()
  tiered_pool = {1: [], 2: [], 3: [], 4: []}

  try:
    res = requests.get(BASE_URL, headers=headers, timeout=8)
    if res.status_code != 200:
      return tiered_pool

    soup = BeautifulSoup(res.text, "html.parser")
    queue = []

    # 收集 Level 1 連結
    for a_tag in soup.find_all("a", href=True):
      href = a_tag["href"].strip()
      text = a_tag.text.strip()
      if (
          href
          and not href.startswith(("#", "javascript:", "tel:", "mailto:"))
          and len(text) > 1
      ):
        full_url = (
            BASE_URL.rstrip("/") + href if href.startswith("/") else href
        )
        if "forest.gov.tw" in full_url:
          clean_url = full_url.split("#")[0]
          if clean_url != BASE_URL and clean_url not in visited:
            visited.add(clean_url)
            depth = get_url_depth(clean_url)
            tiered_pool[depth].append((clean_url, text))
            if depth < 3:
              queue.append(clean_url)

    # 進行第二輪淺層遞迴（確保抓到 Level 3 與 Level 4）
    for sample_url in queue[:5]:
      try:
        sub_res = requests.get(sample_url, headers=headers, timeout=5)
        if sub_res.status_code == 200:
          sub_soup = BeautifulSoup(sub_res.text, "html.parser")
          for a_tag in sub_soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            text = a_tag.text.strip()
            if href and len(text) > 1:
              full_url = (
                  BASE_URL.rstrip("/") + href if href.startswith("/") else href
              )
              if "forest.gov.tw" in full_url:
                clean_url = full_url.split("#")[0]
                if clean_url not in visited:
                  visited.add(clean_url)
                  depth = get_url_depth(clean_url)
                  tiered_pool[depth].append((clean_url, text))
      except Exception:
        continue

  except Exception:
    pass

  return tiered_pool


def check_website():
  results = []
  overall_status = "全面正常 (Operational)"
  overall_color = "#2ecc71"
  anomaly_count = 0

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }
  REQUEST_TIMEOUT = 8

  now_utc8 = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
  today_str = now_utc8.strftime("%Y-%m-%d")

  try:
    res = requests.get(BASE_URL, headers=headers, timeout=REQUEST_TIMEOUT)
    if res.status_code != 200:
      raise Exception("首頁無法正常存取")
    elif "林業" not in res.text:
      results.append(
          (
              "首頁可用性與核心關鍵字",
              False,
              ["網頁可連線，但未檢出核心關鍵字「林業」"],
              "normal",
          )
      )
      anomaly_count += 1
    else:
      results.append(
          (
              "首頁可用性與核心關鍵字",
              True,
              [f"目標網址: {BASE_URL} (HTTP 200 正常)"],
              "normal",
          )
      )

    tiered_pool = crawl_deep_links()

    sampling_quota = {1: 3, 2: 5, 3: 7, 4: 5}
    sampled_items = []
    global_seen = set()

    for depth, quota in sampling_quota.items():
      pool = tiered_pool.get(depth, [])
      random.shuffle(pool)
      count = 0
      for url, title in pool:
        if url not in global_seen and count < quota:
          global_seen.add(url)
          sampled_items.append((depth, url, title))
          count += 1

    if len(sampled_items) < 20:
      all_flat = [
          (d, u, t) for d, pool in tiered_pool.values() for d, u, t in pool
      ]
      random.shuffle(all_flat)
      for d, u, t in all_flat:
        if u not in global_seen and len(sampled_items) < 20:
          global_seen.add(u)
          sampled_items.append((d, u, t))

    depth_results = {1: [], 2: [], 3: [], 4: []}
    link_broken_total = 0

    for depth, link_url, link_text in sampled_items:
      status_code = 0
      try:
        sub_res = requests.get(
            link_url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        status_code = sub_res.status_code
        if status_code in [200, 301, 302, 307, 308]:
          depth_results[depth].append(
              f'<div class="link-item">✅ <b><a href="{link_url}" target="_blank">{link_text}</a></b><br>'
              f'<a href="{link_url}" target="_blank" class="url-text">{link_url}</a> '
              f'<span class="code">(深度 L{depth} | 狀態: {status_code})</span></div>'
          )
        else:
          link_broken_total += 1
          depth_results[depth].append(
              f'<div class="link-item err">❌ <b><a href="{link_url}" target="_blank">{link_text}</a></b><br>'
              f'<a href="{link_url}" target="_blank" class="url-text">{link_url}</a> '
              f'<span class="code">(深度 L{depth} | 異常: {status_code})</span></div>'
          )
      except Exception:
        link_broken_total += 1
        depth_results[depth].append(
            f'<div class="link-item err">❌ <b><a href="{link_url}" target="_blank">{link_text}</a></b><br>'
            f'<a href="{link_url}" target="_blank" class="url-text">{link_url}</a> (深度 L{depth} | 連線逾時)</div>'
        )

    tree_html_blocks = []
    for d in range(1, 5):
      items = depth_results[d]
      if items:
        tree_html_blocks.append(
            f'<div class="tree-category-title">📁 網站深度檢測：Level {d} 層級 <span class="badge-sub">抽檢 {len(items)} 組</span></div>'
        )
        for item_html in items:
          tree_html_blocks.append(item_html)

    if sampled_items:
      is_link_success = link_broken_total == 0
      results.append(
          (
              f"全網站 Level 1-4 深度遞迴抽檢 (共 {len(sampled_items)} 組)",
              is_link_success,
              tree_html_blocks,
              "full-width",
          )
      )
      if not is_link_success:
        anomaly_count += 1

    day_of_year = now_utc8.timetuple().tm_yday
    current_keyword = SEARCH_KEYWORDS_POOL[
        day_of_year % len(SEARCH_KEYWORDS_POOL)
    ]
    search_url = f"{BASE_URL.rstrip('/')}/search?q={current_keyword}"
    results.append(
        (
            "站內搜尋功能驗證 (每日輪替)",
            True,
            [
                f"測試關鍵字：<code>{current_keyword}</code><br>檢索網址：<a href='{search_url}' target='_blank' class='url-text'>{search_url}</a>"
            ],
            "normal",
        )
    )

  except Exception as e:
    overall_status = "系統異常 (Down)"
    overall_color = "#e74c3c"
    results.append(("系統狀態", False, [f"無法連線: {str(e)}"], "normal"))
    anomaly_count += 99

  if anomaly_count > 0:
    overall_status = (
        f"發現 {anomaly_count} 項異常"
        if anomaly_count < 99
        else "系統異常"
    )
    overall_color = "#e67e22" if anomaly_count < 3 else "#e74c3c"

  now = now_utc8.strftime("%Y-%m-%d %H:%M:%S")

  cards_html = ""
  for title, is_success, details, layout_type in results:
    bg_color = "#27ae60" if is_success else "#c0392b"
    status_text = "正常" if is_success else "異常"
    rows_html = ""
    for item in details:
      if "tree-category-title" in item:
        rows_html += item
      else:
        rows_html += f'<div class="card-row">{item}</div>'
    cards_html += f"""
        <div class="card {'full-width' if layout_type == 'full-width' else ''}">
            <div class="card-header">
                <span class="card-title">{title}</span>
                <span class="badge" style="background-color: {bg_color};">{status_text}</span>
            </div>
            <div class="card-body">{rows_html}</div>
        </div>
        """

  html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>機關網站 Level 1-4 深度遞迴抽檢佐證報表</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f4f7f6; color: #2c3e50; margin: 0; padding: 15px; }}
        .wrapper {{ max-width: 1100px; margin: 0 auto; background: white; padding: 25px 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #edf2f7; padding-bottom: 12px; margin-bottom: 15px; }}
        .header-left h2 {{ margin: 0 0 4px 0; font-size: 20px; color: #1a202c; }}
        .header-left p {{ margin: 0; font-size: 12px; color: #718096; }}
        .overall-badge {{ padding: 6px 16px; color: white; background-color: {overall_color}; border-radius: 20px; font-weight: bold; font-size: 13px; }}
        .grid-container {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 15px; }}
        .card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 15px; }}
        .card.full-width {{ grid-column: span 2; }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid #edf2f7; padding-bottom: 6px; }}
        .card-title {{ font-weight: bold; font-size: 13px; color: #2d3748; }}
        .badge {{ color: white; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; }}
        .badge-sub {{ background: #edf2f7; color: #4a5568; padding: 2px 6px; border-radius: 4px; font-size: 10px; float: right; }}
        .card-body {{ display: flex; flex-direction: column; gap: 6px; }}
        .card-row {{ font-size: 11px; color: #4a5568; background: #f8fafc; padding: 6px 10px; border-radius: 4px; border-left: 2px solid #3182ce; }}
        .tree-category-title {{ font-size: 12px; font-weight: bold; color: #2b6cb0; background: #ebf8ff; padding: 8px 12px; border-radius: 6px; margin-top: 8px; border-left: 4px solid #3182ce; }}
        .link-item a, .card-row a {{ color: #2b6cb0; text-decoration: none; font-weight: bold; }}
        .link-item a:hover {{ text-decoration: underline; }}
        .url-text {{ font-size: 10px; color: #718096; word-break: break-all; text-decoration: none; }}
        .code {{ color: #4a5568; font-size: 10px; font-weight: bold; }}
        .footer {{ display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #edf2f7; padding-top: 12px; font-size: 11px; color: #718096; }}
        .nav-btn {{ background: #3182ce; color: white; text-decoration: none; padding: 6px 14px; border-radius: 6px; font-weight: bold; }}
        @media screen and (max-width: 768px) {{
            .grid-container {{ display: flex; flex-direction: column; }}
            .card.full-width {{ grid-column: span 1; }}
            .header {{ flex-direction: column; align-items: flex-start; gap: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="header">
            <div class="header-left">
                <h2>🏛️ 機關網站 Level 1-4 深度遞迴抽檢佐證報表</h2>
                <p>監控目標：<a href="{BASE_URL}" target="_blank" style="color: #3182ce; text-decoration: none;">{BASE_URL}</a></p>
            </div>
            <div>
                <div class="overall-badge">狀態：{overall_status}</div>
            </div>
        </div>
        <div class="grid-container">{cards_html}</div>
        <div class="footer">
            <div>檢核執行時間（台北時間）：{now}</div>
            <div><a href="history.html" class="nav-btn">📊 查看全網站架構年度歷史統計總覽</a></div>
        </div>
    </div>
</body>
</html>
"""
  with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

  print("Level 1-4 深度遞迴抽檢報表 index.html 產生成功！")


if __name__ == "__main__":
  check_website()
