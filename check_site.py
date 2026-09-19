import datetime
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

# 站內搜尋每日輪替題庫（涵蓋林務局核心業務與民眾常用查詢詞）
SEARCH_KEYWORDS_POOL = [
    "步道",
    "森林",
    "保育",
    "志工",
    "國家森林遊樂區",
    "苗木",
    "登山",
]


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

  try:
    # 1. 首頁可用性
    res = requests.get(BASE_URL, headers=headers, timeout=REQUEST_TIMEOUT)
    if res.status_code != 200:
      results.append(
          (
              "首頁可用性與核心關鍵字",
              False,
              [
                  f"目標網址: {BASE_URL}",
                  f"狀態碼異常: {res.status_code}",
              ],
              "normal",
          )
      )
      anomaly_count += 1
      raise Exception("首頁無法正常存取")
    elif "林業" not in res.text:
      results.append(
          (
              "首頁可用性與核心關鍵字",
              False,
              [
                  f"目標網址: {BASE_URL}",
                  "網頁可連線，但未檢出核心關鍵字「林業」",
              ],
              "normal",
          )
      )
      anomaly_count += 1
    else:
      results.append(
          (
              "首頁可用性與核心關鍵字",
              True,
              [
                  f"目標網址: {BASE_URL}",
                  "HTTP 200 正常，成功檢出核心關鍵字「林業」",
              ],
              "normal",
          )
      )

    soup = BeautifulSoup(res.text, "html.parser")

    # ==========================================================
    # 2. 第一層 Link 隨機抽檢 (共 20 組：名稱 + 完整可點擊網址)
    # ==========================================================
    all_menu_links = []
    for a_tag in soup.find_all("a", href=True):
      href = a_tag["href"].strip()
      text = a_tag.text.strip()
      if (
          href
          and not href.startswith(("#", "javascript:", "tel:", "mailto:"))
          and len(text) > 1
      ):
        if href.startswith("/"):
          full_url = BASE_URL.rstrip("/") + href
        elif "forest.gov.tw" in href:
          full_url = href
        else:
          continue

        clean_url = full_url.split("#")[0]
        if clean_url != BASE_URL:
          item = (clean_url, text)
          if item not in all_menu_links:
            all_menu_links.append(item)

    random.shuffle(all_menu_links)
    sampled_menus = all_menu_links[:20]

    link_items = []
    link_broken = 0
    if sampled_menus:
      for link_url, link_text in sampled_menus:
        try:
          sub_res = requests.get(
              link_url,
              headers=headers,
              timeout=REQUEST_TIMEOUT,
              allow_redirects=True,
          )
          if sub_res.status_code in [200, 301, 302, 307, 308]:
            link_items.append(
                f'<div class="link-item">✅ <b><a href="{link_url}" target="_blank">{link_text}</a></b><br>'
                f'<a href="{link_url}" target="_blank" class="url-text">{link_url}</a> '
                f'<span class="code">(狀態: {sub_res.status_code})</span></div>'
            )
          else:
            link_items.append(
                f'<div class="link-item err">❌ <b><a href="{link_url}" target="_blank">{link_text}</a></b><br>'
                f'<a href="{link_url}" target="_blank" class="url-text">{link_url}</a> '
                f'<span class="code">(異常: {sub_res.status_code})</span></div>'
            )
            link_broken += 1
        except Exception:
          link_items.append(
              f'<div class="link-item err">❌ <b><a href="{link_url}" target="_blank">{link_text}</a></b><br>'
              f'<a href="{link_url}" target="_blank" class="url-text">{link_url}</a> (連線逾時)</div>'
          )
          link_broken += 1

      if link_broken == 0:
        results.append(
            ("第一層 Link 隨機抽檢 (共 20 組)", True, link_items, "grid-links")
        )
      else:
        results.append(
            ("第一層 Link 隨機抽檢 (共 20 組)", False, link_items, "grid-links")
        )
        anomaly_count += 1
    else:
      results.append(
          (
              "第一層 Link 隨機抽檢 (共 20 組)",
              True,
              ["未捕捉到足夠的導覽 Link"],
              "normal",
          )
      )

    # ==========================================================
    # 3. 最新公告頁面檢查（抽樣 5 篇：完整標題與絕對路徑網址）
    # ==========================================================
    news_links = []
    for a_tag in soup.find_all("a", href=True):
      href = a_tag["href"]
      text = a_tag.text.strip()
      if (
          any(k in href.lower() for k in ["news", "bulletin", "cp.aspx", "ann"])
          and len(text) > 4
      ):
        full_url = (
            BASE_URL.rstrip("/") + href if href.startswith("/") else href
        )
        if full_url not in [n[0] for n in news_links]:
          news_links.append((full_url, text))

    news_items = []
    news_error = 0
    if len(news_links) > 0:
      for n_url, n_title in news_links[:5]:
        try:
          n_res = requests.get(n_url, headers=headers, timeout=REQUEST_TIMEOUT)
          if n_res.status_code == 200:
            news_items.append(
                f'<div class="news-item">✅ <b><a href="{n_url}" target="_blank">{n_title}</a></b><br>'
                f'<a href="{n_url}" target="_blank" class="url-text">{n_url}</a> <span class="tag">正常載入</span></div>'
            )
          else:
            news_items.append(
                f'<div class="news-item err">❌ <b><a href="{n_url}" target="_blank">{n_title}</a></b><br>'
                f'<a href="{n_url}" target="_blank" class="url-text">{n_url}</a> <span class="tag-err">異常({n_res.status_code})</span></div>'
            )
            news_error += 1
        except Exception:
          news_items.append(
              f'<div class="news-item err">❌ <b><a href="{n_url}" target="_blank">{n_title}</a></b><br>'
              f'<a href="{n_url}" target="_blank" class="url-text">{n_url}</a> <span class="tag-err">連線逾時</span></div>'
          )
          news_error += 1

      if news_error == 0:
        results.append(("最新公告頁面有效性 (抽樣 5 篇)", True, news_items, "full-card"))
      else:
        results.append(
            ("最新公告頁面有效性 (抽樣 5 篇)", False, news_items, "full-card")
        )
        anomaly_count += 1
    else:
      results.append(
          (
              "最新公告頁面有效性 (抽樣 5 篇)",
              True,
              ["未捕捉到公告結構"],
              "full-card",
          )
      )

    # 4. 官方核心服務與專區可用性驗證
    service_items = []
    service_error = 0
    for page in CORE_SERVICE_PAGES:
      p_name = page["name"]
      p_url = page["url"]
      try:
        s_res = requests.get(p_url, headers=headers, timeout=REQUEST_TIMEOUT)
        if s_res.status_code == 200:
          service_items.append(
              f'✅ <a href="{p_url}" target="_blank"><b>{p_name}</b></a><br>'
              f'<a href="{p_url}" target="_blank" class="url-text">{p_url}</a> (狀態碼: 200 正常)'
          )
        else:
          service_items.append(
              f'❌ <a href="{p_url}" target="_blank"><b>{p_name}</b></a><br>'
              f'<a href="{p_url}" target="_blank" class="url-text">{p_url}</a> (異常代碼: {s_res.status_code})'
          )
          service_error += 1
      except Exception:
        service_items.append(
            f'❌ <a href="{p_url}" target="_blank"><b>{p_name}</b></a><br>'
            f'<a href="{p_url}" target="_blank" class="url-text">{p_url}</a> (連線逾時)'
        )
        service_error += 1

    if service_error == 0:
      results.append(
          ("官方核心服務與專區可用性驗證", True, service_items, "full-card")
      )
    else:
      results.append(
          ("官方核心服務與專區可用性驗證", False, service_items, "full-card")
      )
      anomaly_count += 1

    # ==========================================================
    # 5. 站內搜尋功能驗證（依日期自動輪替題庫中的關鍵字）
    # ==========================================================
    now_utc8 = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    day_of_year = now_utc8.timetuple().tm_yday
    current_keyword = SEARCH_KEYWORDS_POOL[
        day_of_year % len(SEARCH_KEYWORDS_POOL)
    ]

    search_url = f"{BASE_URL.rstrip('/')}/search?q={current_keyword}"
    try:
      s_res = requests.get(search_url, headers=headers, timeout=REQUEST_TIMEOUT)
      if s_res.status_code == 200 and len(s_res.text) > 300:
        results.append(
            (
                "站內搜尋功能驗證 (每日輪替)",
                True,
                [
                    f'輪替測試關鍵字：<code>{current_keyword}</code><br>'
                    f'檢索網址：<a href="{search_url}" target="_blank" class="url-text">{search_url}</a> (狀態碼: {s_res.status_code}) - 檢索引擎運作正常'
                ],
                "full-card",
            )
        )
      else:
        results.append(
            (
                "站內搜尋功能驗證 (每日輪替)",
                False,
                [
                    f'輪替測試關鍵字：<code>{current_keyword}</code><br>'
                    f'檢索網址：<a href="{search_url}" target="_blank" class="url-text">{search_url}</a> (異常代碼)'
                ],
                "full-card",
            )
        )
        anomaly_count += 1
    except Exception:
      results.append(
          (
              "站內搜尋功能驗證 (每日輪替)",
              False,
              [
                  f"輪替測試關鍵字：<code>{current_keyword}</code><br>搜尋模組連線逾時"
              ],
              "full-card",
          )
      )
      anomaly_count += 1

  except Exception as e:
    overall_status = "系統異常 (Down)"
    overall_color = "#e74c3c"
    results.append(("系統狀態", False, [f"無法連線: {str(e)}"], "full-card"))
    anomaly_count += 99

  if anomaly_count > 0:
    overall_status = f"發現 {anomaly_count} 項異常"
    overall_color = "#e67e22" if anomaly_count < 3 else "#e74c3c"

  now = now_utc8.strftime("%Y-%m-%d %H:%M:%S")

  cards_html = ""
  for title, is_success, details, layout_type in results:
    bg_color = "#27ae60" if is_success else "#c0392b"
    status_text = "正常" if is_success else "異常"

    if layout_type == "grid-links":
      rows_html = '<div class="links-grid">'
      for item in details:
        rows_html += f'<div class="link-cell">{item}</div>'
      rows_html += "</div>"
    else:
      rows_html = ""
      for item in details:
        rows_html += f'<div class="card-row">{item}</div>'

    cards_html += f"""
        <div class="card {'full-width' if layout_type == 'full-width' or layout_type == 'grid-links' else ''}">
            <div class="card-header">
                <span class="card-title">{title}</span>
                <span class="badge" style="background-color: {bg_color};">{status_text}</span>
            </div>
            <div class="card-body">
                {rows_html}
            </div>
        </div>
        """

  html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>機關網站日常檢核佐證報表</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f4f7f6; color: #2c3e50; margin: 0; padding: 15px; }}
        .wrapper {{ max-width: 1100px; margin: 0 auto; background: white; padding: 25px 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #edf2f7; padding-bottom: 12px; margin-bottom: 15px; }}
        .header-left h2 {{ margin: 0 0 4px 0; font-size: 20px; color: #1a202c; }}
        .header-left p {{ margin: 0; font-size: 12px; color: #718096; }}
        .overall-badge {{ padding: 6px 16px; color: white; background-color: {overall_color}; border-radius: 20px; font-weight: bold; font-size: 13px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        
        .grid-container {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 15px; }}
        .card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }}
        .card.full-width {{ grid-column: span 2; }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid #edf2f7; padding-bottom: 6px; }}
        .card-title {{ font-weight: bold; font-size: 13px; color: #2d3748; }}
        .badge {{ color: white; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; }}
        
        .card-body {{ display: flex; flex-direction: column; gap: 6px; }}
        .card-row {{ font-size: 11px; color: #4a5568; background: #f8fafc; padding: 6px 10px; border-radius: 4px; border-left: 2px solid #3182ce; line-height: 1.4; }}
        
        .links-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }}
        .link-cell {{ font-size: 11px; background: #f8fafc; padding: 6px 10px; border-radius: 4px; border-left: 2px solid #3182ce; color: #2d3748; line-height: 1.4; }}
        .link-item a {{ color: #2b6cb0; text-decoration: none; font-weight: bold; }}
        .link-item a:hover {{ text-decoration: underline; }}
        
        .url-text {{ font-size: 10px; color: #718096; word-break: break-all; text-decoration: none; }}
        .url-text:hover {{ text-decoration: underline; color: #3182ce; }}
        
        .code {{ color: #4a5568; font-size: 10px; font-weight: bold; }}

        .news-item, .card-row {{ font-size: 11px; color: #4a5568; background: #f8fafc; padding: 6px 10px; border-radius: 4px; border-left: 2px solid #3182ce; line-height: 1.4; }}
        .news-item a {{ color: #2b6cb0; text-decoration: none; font-weight: bold; }}
        .news-item a:hover {{ text-decoration: underline; }}

        .tag {{ background: #e2e8f0; color: #4a5568; padding: 1px 4px; border-radius: 3px; font-size: 10px; float: right; }}
        .tag-err {{ background: #fed7d7; color: #c53030; padding: 1px 4px; border-radius: 3px; font-size: 10px; float: right; }}

        .footer {{ display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #edf2f7; padding-top: 12px; font-size: 11px; color: #718096; }}
        .print-btn {{ background: #3182ce; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: bold; box-shadow: 0 1px 3px rgba(49,130,206,0.3); }}
        .print-btn:hover {{ background: #2b6cb0; }}

        @media print {{
            @page {{ size: A4 portrait; margin: 10mm; }}
            body {{ background: white; padding: 0; zoom: 90%; }}
            .wrapper {{ box-shadow: none; padding: 0; max-width: 100%; }}
            .print-btn {{ display: none; }}
            .card {{ break-inside: avoid; border: 1px solid #cbd5e0; }}
        }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="header">
            <div class="header-left">
                <h2>🏛️ 機關網站核心功能每日檢核暨動態佐證報表</h2>
                <p>監控目標：<a href="{BASE_URL}" target="_blank" style="color: #3182ce; text-decoration: none;">{BASE_URL}</a></p>
            </div>
            <div>
                <div class="overall-badge">狀態：{overall_status}</div>
            </div>
        </div>

        <div class="grid-container">
            {cards_html}
        </div>

        <div class="footer">
            <div>檢核執行時間（台北時間）：{now}</div>
            <div><button class="print-btn" onclick="window.print()">🖨️ 列印 / 儲存為正式 PDF 單頁報表</button></div>
        </div>
    </div>
</body>
</html>
"""

  with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
  print("搜尋關鍵字每日輪替版報表 index.html 產生成功！")


if __name__ == "__main__":
  check_website()
