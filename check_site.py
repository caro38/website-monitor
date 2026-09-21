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
  """計算網址的深度（依斜線數量判定）"""
  clean_path = url.replace(BASE_URL.rstrip("/"), "")
  parts = [p for p in clean_path.split("/") if p]
  depth = len(parts)
  return max(1, min(depth, 4))


def crawl_deep_links():
  """遞迴爬蟲：收集至多 Level 4 的內部連結"""
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


def update_and_save_history(today_str, sampled_results):
  """讀取並更新年度歷史資料庫 (JSON)"""
  history_data = []
  if os.path.exists(HISTORY_FILE):
    try:
      with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        history_data = json.load(f)
    except Exception:
      history_data = []

  # 移除今天可能已存在的舊紀錄（避免重複執行覆蓋）
  history_data = [h for h in history_data if h.get("date") != today_str]

  # 新增今天的紀錄
  history_data.append({"date": today_str, "items": sampled_results})

  with open(HISTORY_FILE, "w", encoding="utf-8") as f:
    json.dump(history_data, f, ensure_ascii=False, indent=2)

  return history_data


def generate_history_html(history_data):
  """產生以網站架構為主軸的歷史統計頁面 (history.html)"""
  # 將資料重新梳理為：{ depth: { url: { "title": ..., "history": [ {date, status, ok}, ... ] } } }
  tree_structure = {1: {}, 2: {}, 3: {}, 4: {}}

  for record in history_data:
    date_str = record["date"]
    for item in record["items"]:
      d = item["depth"]
      url = item["url"]
      title = item["title"]
      status = item["status"]
      ok = item["ok"]

      if url not in tree_structure[d]:
        tree_structure[d][url] = {"title": title, "history": []}

      # 避免同一天重複紀錄
      tree_structure[d][url]["history"].append({
          "date": date_str,
          "status": status,
          "ok": ok,
      })

  # 組裝 HTML 內容
  tree_html = ""
  total_tracked_urls = sum(len(v) for v in tree_structure.values())

  for d in range(1, 5):
    items_dict = tree_structure[d]
    if items_dict:
      tree_html += f"""
            <div class="level1-box">
                <div class="level1-header">
                    <span>📁 網站架構層級：Level {d} 深度目錄</span>
                    <span style="font-size: 11px; color: #4a5568;">累計追蹤網頁：{len(items_dict)} 個</span>
                </div>
                <div class="level1-body">
            """
      for url, data in items_dict.items():
        badges_html = ""
        # 依日期排序軌跡
        sorted_history = sorted(
            data["history"], key=lambda x: x["date"], reverse=True
        )
        for h in sorted_history:
          b_class = "ok" if h["ok"] else "err"
          b_text = (
              f"{h['date']} ({h['status']} 正常)"
              if h["ok"]
              else f"{h['date']} ({h['status']} 異常)"
          )
          badges_html += (
              f'<span class="record-badge {b_class}">{b_text}</span>'
          )

        tree_html += f"""
                <div class="level2-item">
                    <div class="item-info">
                        <div>
                            <div class="item-title">📄 <b><a href="{url}" target="_blank">{data['title']}</a></b></div>
                            <div class="item-url">路徑：{url}</div>
                        </div>
                    </div>
                    <div class="audit-history-strip">
                        <span class="history-label">歷次抽檢軌跡：</span>
                        {badges_html}
                    </div>
                </div>
                """
      tree_html += "</div></div>"

  history_html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>機關網站架構化檢核軌跡與歷史統計總覽</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f4f7f6; color: #2c3e50; margin: 0; padding: 20px; }}
        .wrapper {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .header {{ border-bottom: 2px solid #edf2f7; padding-bottom: 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
        .header h2 {{ margin: 0 0 5px 0; font-size: 22px; color: #1a202c; }}
        .header p {{ margin: 0; font-size: 13px; color: #718096; }}
        .back-btn {{ background: #4a5568; color: white; text-decoration: none; padding: 6px 14px; border-radius: 6px; font-size: 12px; font-weight: bold; }}
        .back-btn:hover {{ background: #2d3748; }}
        
        .tree-root {{ display: flex; flex-direction: column; gap: 20px; }}
        .level1-box {{ border: 1px solid #cbd5e0; border-radius: 8px; background: #ffffff; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }}
        .level1-header {{ background: #ebf8ff; padding: 12px 18px; font-weight: bold; font-size: 14px; color: #2b6cb0; border-bottom: 1px solid #cbd5e0; display: flex; justify-content: space-between; align-items: center; border-left: 5px solid #3182ce; }}
        .level1-body {{ padding: 15px; display: flex; flex-direction: column; gap: 12px; }}
        
        .level2-item {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; display: flex; flex-direction: column; gap: 8px; }}
        .item-title a {{ color: #2b6cb0; text-decoration: none; font-weight: bold; font-size: 12px; }}
        .item-title a:hover {{ text-decoration: underline; }}
        .item-url {{ font-size: 10px; color: #718096; word-break: break-all; margin-top: 2px; }}
        
        .audit-history-strip {{ background: #ffffff; border: 1px dashed #cbd5e0; border-radius: 4px; padding: 6px 10px; font-size: 11px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
        .history-label {{ font-weight: bold; color: #4a5568; font-size: 10px; }}
        .record-badge {{ background: #edf2f7; color: #2d3748; padding: 2px 6px; border-radius: 3px; font-size: 10px; border: 1px solid #cbd5e0; }}
        .record-badge.ok {{ background: #f0fff4; color: #27ae60; border-color: #c6f6d5; }}
        .record-badge.err {{ background: #fff5f5; color: #c0392b; border-color: #fed7d7; }}
        
        @media screen and (max-width: 768px) {{
            .wrapper {{ padding: 15px; }}
        }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="header">
            <div class="header-left">
                <h2>🌳 網站架構化檢核軌跡與歷史統計總覽</h2>
                <p>呈現主軸：以林業及自然保育署全網站 Level 架構分類，累計追蹤網頁數：{total_tracked_urls} 個</p>
            </div>
            <div>
                <a href="index.html" class="back-btn">⬅️ 返回今日即時檢核報表</a>
            </div>
        </div>
        <div class="tree-root">
            {tree_html}
        </div>
    </div>
</body>
</html>
"""
  with open("history.html", "w", encoding="utf-8") as f:
    f.write(history_html_content)


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
    today_audit_records = []

    for depth, link_url, link_text in sampled_items:
      status_code = 0
      is_ok = False
      try:
        sub_res = requests.get(
            link_url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        status_code = sub_res.status_code
        if status_code in [200, 301, 302, 307, 308]:
          is_ok = True
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

      today_audit_records.append({
          "title": link_text,
          "url": link_url,
          "depth": depth,
          "status": status_code,
          "ok": is_ok,
      })

    # 更新歷史 JSON 並生成 history.html
    history_data = update_and_save_history(today_str, today_audit_records)
    generate_history_html(history_data)

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

  print("即時報表與歷史統計產生器執行完畢！")


if __name__ == "__main__":
  check_website()
