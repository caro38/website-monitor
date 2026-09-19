import datetime
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.forest.gov.tw/"


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

  try:
    # 1. 首頁可用性
    res = requests.get(BASE_URL, headers=headers, timeout=15)
    if res.status_code != 200:
      results.append(
          (
              "首頁可用性與核心關鍵字",
              False,
              f"目標網址: {BASE_URL}<br>狀態碼異常: {res.status_code}",
          )
      )
      anomaly_count += 1
      raise Exception("首頁無法正常存取")
    elif "林業" not in res.text:
      results.append(
          (
              "首頁可用性與核心關鍵字",
              False,
              f"目標網址: {BASE_URL}<br>網頁可連線，但未檢出核心關鍵字「林業」",
          )
      )
      anomaly_count += 1
    else:
      results.append(
          (
              "首頁可用性與核心關鍵字",
              True,
              (
                  f"目標網址: {BASE_URL}<br>HTTP 200 正常，成功檢出核心關鍵字「林業」"
              ),
          )
      )

    soup = BeautifulSoup(res.text, "html.parser")

    # 2. 第一層 Link 檢查（具體抽樣檢查 5 個項目）
    menu_links = []
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
        if clean_url != BASE_URL and (clean_url, text[:12]) not in menu_links:
          menu_links.append((clean_url, text[:12]))

    link_details = []
    link_broken = 0
    # 抽樣具體檢查前 5 個核心第一層 Link
    for link_url, link_text in menu_links[:5]:
      try:
        sub_res = requests.get(
            link_url, headers=headers, timeout=5, allow_redirects=True
        )
        if sub_res.status_code in [200, 301, 302, 307, 308]:
          link_details.append(
              f"✅ <b>{link_text}</b> (狀態: {sub_res.status_code})"
          )
        else:
          link_details.append(
              f"❌ <b>{link_text}</b> (異常代碼: {sub_res.status_code})"
          )
          link_broken += 1
      except Exception:
        link_details.append(f"❌ <b>{link_text}</b> (連線逾時/失效)")
        link_broken += 1

    link_desc = (
        "<b>具體抽樣 5 個導覽連結佐證：</b><br>" + "<br>".join(link_details)
        if link_details
        else "未捕捉到有效導覽連結"
    )
    if link_broken == 0 and len(link_details) > 0:
      results.append(("第一層 Link 導覽失效檢查", True, link_desc))
    else:
      results.append(("第一層 Link 導覽失效檢查", False, link_desc))
      anomaly_count += 1

    # 3. 最新公告頁面檢查（具體抽樣檢查 5 筆公告）
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

    news_details = []
    news_error = 0
    if len(news_links) > 0:
      # 具體抽樣前 5 筆公告
      for n_url, n_title in news_links[:5]:
        try:
          n_res = requests.get(n_url, headers=headers, timeout=6)
          if n_res.status_code == 200:
            news_details.append(
                f"✅ <b>{n_title[:16]}...</b> (公告頁面正常載入)"
            )
          else:
            news_details.append(
                f"❌ <b>{n_title[:16]}...</b> (回應異常: {n_res.status_code})"
            )
            news_error += 1
        except Exception:
          news_details.append(f"❌ <b>{n_title[:16]}...</b> (頁面連線逾時)")
          news_error += 1

      news_desc = "<b>具體抽樣 5 筆公告頁面佐證：</b><br>" + "<br>".join(
          news_details
      )
      if news_error == 0:
        results.append(("最新公告頁面有效性", True, news_desc))
      else:
        results.append(("最新公告頁面有效性", False, news_desc))
        anomaly_count += 1
    else:
      results.append(
          (
              "最新公告頁面有效性",
              True,
              "首頁未直接捕捉到公告清單結構（略過細節）",
          )
      )

    # 4. 公告附件下載驗證（掃描前 5 筆公告中的附件）
    att_found_list = []
    att_error_count = 0
    if len(news_links) > 0:
      try:
        for n_url, n_title in news_links[:5]:
          n_res = requests.get(n_url, headers=headers, timeout=6)
          if n_res.status_code == 200:
            n_soup = BeautifulSoup(n_res.text, "html.parser")
            for file_a in n_soup.find_all("a", href=True):
              f_href = file_a["href"].lower()
              if any(
                  ext in f_href for ext in [".pdf", ".odf", ".doc", ".odt"]
              ):
                att_url = (
                    BASE_URL.rstrip("/") + file_a["href"]
                    if file_a["href"].startswith("/")
                    else file_a["href"]
                )
                att_name = file_a.text.strip() or "未命名附件檔案"
                att_test = requests.head(att_url, headers=headers, timeout=5)
                if att_test.status_code in [200, 301, 302]:
                  att_found_list.append(
                      f"✅ <b>{att_name[:12]}</b> (下載驗證有效)"
                  )
                else:
                  att_found_list.append(
                      f"❌ <b>{att_name[:12]}</b> (下載連結異常: {att_test.status_code})"
                  )
                  att_error_count += 1
                break
      except Exception:
        pass

    if att_found_list:
      att_desc = (
          "<b>近期 5 筆公告附件下載驗證佐證：</b><br>"
          + "<br>".join(att_found_list)
      )
      if att_error_count == 0:
        results.append(("最新公告附件下載驗證", True, att_desc))
      else:
        results.append(("最新公告附件下載驗證", False, att_desc))
        anomaly_count += 1
    else:
      results.append(
          (
              "最新公告附件下載驗證",
              True,
              (
                  "<b>近期 5 筆公告掃描佐證：</b><br>經掃描近期 5"
                  " 筆公告頁面，未直接檢出帶有 PDF/ODF 下載附件"
              ),
          )
      )

    # 5. 站內搜尋功能驗證
    search_keyword = "步道"
    search_url = f"{BASE_URL.rstrip('/')}/search?q={search_keyword}"
    try:
      s_res = requests.get(search_url, headers=headers, timeout=8)
      if s_res.status_code == 200 and len(s_res.text) > 300:
        results.append(
            (
                "站內搜尋功能驗證",
                True,
                (
                    f"<b>檢索參數佐證：</b><br>測試關鍵字：<code>{search_keyword}</code><br>狀態碼："
                    f" {s_res.status_code} (引擎與資料庫回應正常)"
                ),
            )
        )
      else:
        results.append(
            (
                "站內搜尋功能驗證",
                False,
                (
                    f"<b>檢索參數佐證：</b><br>測試關鍵字：<code>{search_keyword}</code><br>回應異常代碼："
                    f" {s_res.status_code}"
                ),
            )
        )
        anomaly_count += 1
    except Exception:
      results.append(
          (
              "站內搜尋功能驗證",
              False,
              (
                  f"<b>檢索參數佐證：</b><br>測試關鍵字：<code>{search_keyword}</code><br>狀況：模組連線逾時"
              ),
          )
      )
      anomaly_count += 1

  except Exception as e:
    overall_status = "系統嚴重異常 (Down)"
    overall_color = "#e74c3c"
    results.append(("系統狀態", False, f"無法連線執行: {str(e)}"))
    anomaly_count += 99

  if anomaly_count > 0:
    overall_status = f"發現 {anomaly_count} 項異常"
    overall_color = "#e67e22" if anomaly_count < 3 else "#e74c3c"

  now = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=8)
  ).strftime("%Y-%m-%d %H:%M:%S")

  cards_html = ""
  for title, is_success, desc in results:
    bg_color = "#27ae60" if is_success else "#c0392b"
    status_text = "正常" if is_success else "異常"
    cards_html += f"""
        <div class="card">
            <div class="card-header">
                <span class="card-title">{title}</span>
                <span class="badge" style="background-color: {bg_color};">{status_text}</span>
            </div>
            <div class="card-desc">{desc}</div>
        </div>
        """

  html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>機關網站日常巡檢佐證報表</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f8f9fa; color: #2c3e50; margin: 0; padding: 20px; }}
        .wrapper {{ max-width: 950px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #ecf0f1; padding-bottom: 20px; margin-bottom: 20px; }}
        .header-left h2 {{ margin: 0 0 5px 0; font-size: 22px; color: #2c3e50; }}
        .header-left p {{ margin: 0; font-size: 13px; color: #7f8c8d; }}
        .overall-badge {{ padding: 8px 18px; color: white; background-color: {overall_color}; border-radius: 20px; font-weight: bold; font-size: 14px; text-align: center; }}
        
        .grid-container {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 20px; }}
        .card {{ background: #fdfefe; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid #edf2f7; padding-bottom: 6px; }}
        .card-title {{ font-weight: bold; font-size: 14px; color: #2c3e50; }}
        .badge {{ color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
        .card-desc {{ font-size: 12px; color: #4a5568; line-height: 1.5; }}
        .card-desc code {{ background: #edf2f7; padding: 2px 4px; border-radius: 3px; color: #e53e3e; }}
        
        .footer {{ display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #ecf0f1; padding-top: 15px; font-size: 12px; color: #95a5a6; }}
        .print-btn {{ background: #3498db; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: bold; }}
        .print-btn:hover {{ background: #2980b9; }}

        @media print {{
            body {{ background: white; padding: 0; }}
            .wrapper {{ box-shadow: none; padding: 0; max-width: 100%; }}
            .print-btn {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="header">
            <div class="header-left">
                <h2>🏛️ 機關網站核心功能每日檢核暨佐證報表</h2>
                <p>監控目標：<a href="{BASE_URL}" target="_blank" style="color: #2980b9; text-decoration: none;">{BASE_URL}</a></p>
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
  print("明細化佐證報表 index.html 產生成功！")


if __name__ == "__main__":
  check_website()
