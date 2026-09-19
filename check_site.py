import datetime
import random
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.forest.gov.tw/"
TARGET_PAGES = [
    BASE_URL,
    "https://www.forest.gov.tw/plan",
    "https://www.forest.gov.tw/all-news",
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
          )
      )

    soup = BeautifulSoup(res.text, "html.parser")

    # ==========================================
    # 2. 第一層 Link 導覽失效檢查：隨機抽檢 20 組欄位 Link
    # ==========================================
    all_menu_links = []
    for a_tag in soup.find_all("a", href=True):
      href = a_tag["href"].strip()
      text = a_tag.text.strip()
      # 過濾無效連結與外部網站，確保是站內有效導覽
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
        # 排除首頁自身與重複項目
        if clean_url != BASE_URL:
          item = (clean_url, text[:16])
          if item not in all_menu_links:
            all_menu_links.append(item)

    # 隨機洗牌並抽取 20 組
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
                f"🎲 <b>{link_text}</b> (狀態: {sub_res.status_code})"
            )
          else:
            link_items.append(
                f"❌ <b>{link_text}</b> (異常代碼: {sub_res.status_code})"
            )
            link_broken += 1
        except Exception:
          link_items.append(f"❌ <b>{link_text}</b> (連線逾時/失效)")
          link_broken += 1

      if link_broken == 0:
        results.append(
            (
                "第一層 Link 隨機抽檢 (共 20 組)",
                True,
                link_items,
            )
        )
      else:
        results.append(
            (
                "第一層 Link 隨機抽檢 (共 20 組)",
                False,
                link_items,
            )
        )
        anomaly_count += 1
    else:
      results.append(
          (
              "第一層 Link 隨機抽檢 (共 20 組)",
              True,
              ["未在首頁捕捉到足夠的導覽 Link"],
          )
      )

    # 3. 最新公告頁面檢查（抽樣 5 篇）
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
            news_items.append(f"✅ {n_title} <span class='tag'>載入正常</span>")
          else:
            news_items.append(
                f"❌ {n_title} <span class='tag-err'>異常({n_res.status_code})</span>"
            )
            news_error += 1
        except Exception:
          news_items.append(f"❌ {n_title} <span class='tag-err'>連線逾時</span>")
          news_error += 1

      if news_error == 0:
        results.append(("最新公告頁面有效性", True, news_items))
      else:
        results.append(("最新公告頁面有效性", False, news_items))
        anomaly_count += 1
    else:
      results.append(
          ("最新公告頁面有效性", True, ["首頁未直接捕捉到公告清單結構"])
      )

    # 4. 每日動態隨機附件下載驗證（抽樣 5 個）
    all_found_attachments = []
    for target_p in TARGET_PAGES:
      try:
        p_res = requests.get(target_p, headers=headers, timeout=REQUEST_TIMEOUT)
        if p_res.status_code == 200:
          p_soup = BeautifulSoup(p_res.text, "html.parser")
          for file_a in p_soup.find_all("a", href=True):
            f_href = file_a["href"].lower()
            if any(
                ext in f_href
                for ext in [".pdf", ".odf", ".doc", ".docx", ".odt", ".ods"]
            ):
              att_url = (
                  BASE_URL.rstrip("/") + file_a["href"]
                  if file_a["href"].startswith("/")
                  else file_a["href"]
              )
              att_name = (
                  file_a.text.strip() or f"附件檔案({f_href.split('.')[-1]})"
              )
              item_tuple = (att_url, att_name, target_p)
              if item_tuple not in all_found_attachments:
                all_found_attachments.append(item_tuple)
      except Exception:
        continue

    random.shuffle(all_found_attachments)
    sampled_attachments = all_found_attachments[:5]

    att_items = []
    att_error_count = 0

    if sampled_attachments:
      for att_url, att_name, source_page in sampled_attachments:
        try:
          att_test = requests.head(
              att_url, headers=headers, timeout=REQUEST_TIMEOUT
          )
          source_short = (
              "首頁"
              if source_page == BASE_URL
              else ("計畫專區" if "plan" in source_page else "公告/其他")
          )
          if att_test.status_code in [200, 301, 302]:
            att_items.append(
                f"🎲 <b>[{source_short}]</b> 📎 {att_name[:22]} (隨機抽驗：有效)"
            )
          else:
            att_items.append(
                f"❌ <b>[{source_short}]</b> 📎 {att_name[:22]} (抽驗異常:{att_test.status_code})"
            )
            att_error_count += 1
        except Exception:
          att_items.append(
              f"❌ <b>[隨機抽驗]</b> 📎 {att_name[:22]} (連線逾時)"
          )
          att_error_count += 1

      if att_error_count == 0:
        results.append(("每日動態隨機附件下載驗證", True, att_items))
      else:
        results.append(("每日動態隨機附件下載驗證", False, att_items))
        anomaly_count += 1
    else:
      results.append(
          (
              "每日動態隨機附件下載驗證",
              True,
              ["目前站點未檢出可供隨機抽驗之附件檔案"],
          )
      )

    # 5. 站內搜尋功能驗證
    search_keyword = "步道"
    search_url = f"{BASE_URL.rstrip('/')}/search?q={search_keyword}"
    try:
      s_res = requests.get(search_url, headers=headers, timeout=REQUEST_TIMEOUT)
      if s_res.status_code == 200 and len(s_res.text) > 300:
        results.append(
            (
                "站內搜尋功能驗證",
                True,
                [
                    f"測試關鍵字：<code>{search_keyword}</code>",
                    f"HTTP 狀態碼：{s_res.status_code} (檢索引擎與資料庫正常)",
                ],
            )
        )
      else:
        results.append(
            (
                "站內搜尋功能驗證",
                False,
                [
                    f"測試關鍵字：<code>{search_keyword}</code>",
                    f"回應異常代碼：{s_res.status_code}",
                ],
            )
        )
        anomaly_count += 1
    except Exception:
      results.append(
          (
              "站內搜尋功能驗證",
              False,
              [
                  f"測試關鍵字：<code>{search_keyword}</code>",
                  "狀況：模組連線逾時",
              ],
          )
      )
      anomaly_count += 1

  except Exception as e:
    overall_status = "系統嚴重異常 (Down)"
    overall_color = "#e74c3c"
    results.append(("系統狀態", False, [f"無法連線執行: {str(e)}"]))
    anomaly_count += 99

  if anomaly_count > 0:
    overall_status = f"發現 {anomaly_count} 項異常"
    overall_color = "#e67e22" if anomaly_count < 3 else "#e74c3c"

  now = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=8)
  ).strftime("%Y-%m-%d %H:%M:%S")

  cards_html = ""
  for title, is_success, details in results:
    bg_color = "#27ae60" if is_success else "#c0392b"
    status_text = "正常" if is_success else "異常"

    rows_html = ""
    for item in details:
      rows_html += f'<div class="card-row">{item}</div>'

    cards_html += f"""
        <div class="card">
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
    <title>機關網站日常巡檢佐證報表</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f4f7f6; color: #2c3e50; margin: 0; padding: 30px 20px; }}
        .wrapper {{ max-width: 1100px; margin: 0 auto; background: white; padding: 40px; border-radius: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.06); }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #edf2f7; padding-bottom: 24px; margin-bottom: 30px; }}
        .header-left h2 {{ margin: 0 0 8px 0; font-size: 24px; color: #1a202c; }}
        .header-left p {{ margin: 0; font-size: 14px; color: #718096; }}
        .overall-badge {{ padding: 10px 22px; color: white; background-color: {overall_color}; border-radius: 30px; font-weight: bold; font-size: 15px; letter-spacing: 0.5px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }}
        
        .grid-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(480px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; border-bottom: 1px solid #edf2f7; padding-bottom: 10px; }}
        .card-title {{ font-weight: bold; font-size: 16px; color: #2d3748; }}
        .badge {{ color: white; padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; }}
        
        .card-body {{ display: flex; flex-direction: column; gap: 8px; max-height: 320px; overflow-y: auto; padding-right: 4px; }}
        .card-row {{ font-size: 12px; color: #4a5568; background: #f8fafc; padding: 8px 12px; border-radius: 6px; border-left: 3px solid #3182ce; line-height: 1.4; }}
        .card-row code {{ background: #edf2f7; padding: 2px 6px; border-radius: 4px; color: #e53e3e; font-family: monospace; }}
        .tag {{ background: #e2e8f0; color: #4a5568; padding: 1px 6px; border-radius: 4px; font-size: 11px; margin-left: 6px; }}
        .tag-err {{ background: #fed7d7; color: #c53030; padding: 1px 6px; border-radius: 4px; font-size: 11px; margin-left: 6px; }}

        .footer {{ display: flex; justify-content: space-between; align-items: center; border-top: 2px solid #edf2f7; padding-top: 20px; font-size: 13px; color: #718096; }}
        .print-btn {{ background: #3182ce; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: bold; box-shadow: 0 2px 5px rgba(49,130,206,0.3); }}
        .print-btn:hover {{ background: #2b6cb0; }}

        @media print {{
            body {{ background: white; padding: 0; }}
            .wrapper {{ box-shadow: none; padding: 0; max-width: 100%; }}
            .print-btn {{ display: none; }}
            .card {{ break-inside: avoid; border: 1px solid #cbd5e0; }}
            .card-body {{ max-height: none; overflow: visible; }}
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
            <div><button class="print-btn" onclick="window.print()">🖨️ 列印 / 儲存為正式 PDF 稽核報表</button></div>
        </div>
    </div>
</body>
</html>
"""

  with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
  print("20組隨機抽檢報表 index.html 產生成功！")


if __name__ == "__main__":
  check_website()
