import datetime
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.forest.gov.tw/"


def check_website():
  results = []
  overall_status = "正常 (Operational)"
  overall_color = "#28a745"  # 綠色

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }

  # --- 項目 1：檢查首頁連線與關鍵字 ---
  try:
    res = requests.get(BASE_URL, headers=headers, timeout=15)
    if res.status_code != 200:
      results.append(
          ("首頁可用性 (Homepage)", False, f"狀態碼異常: {res.status_code}")
      )
      overall_status = "部分異常"
      overall_color = "#dc3545"
    elif "林業" not in res.text:
      results.append(
          (
              "首頁可用性 (Homepage)",
              False,
              "網頁可連線，但關鍵字「林業」未出現",
          )
      )
      overall_status = "內容異常"
      overall_color = "#ffc107"
    else:
      results.append(
          ("首頁可用性 (Homepage)", True, "首頁連線正常，關鍵字吻合")
      )

      # --- 項目 2：自動抓取首頁的導覽選單與最新公告進行檢測 ---
      soup = BeautifulSoup(res.text, "html.parser")

      # 收集頁面上的重要連結進行檢測 (最多抽樣檢查前 5 個內部連結)
      links_checked = 0
      for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # 過濾內部連結
        if href.startswith("/") or "forest.gov.tw" in href:
          if href.startswith("/"):
            full_url = BASE_URL.rstrip("/") + href
          else:
            full_url = href

          # 簡單抽樣 3 個不同連結測試，避免請求過多
          if links_checked < 3 and full_url != BASE_URL:
            try:
              sub_res = requests.get(
                  full_url, headers=headers, timeout=5, allow_redirects=True
              )
              if sub_res.status_code == 200:
                results.append(
                    (
                        f"內部單元連結檢查 ({a_tag.text.strip()[:10]}...)",
                        True,
                        "連結正常開啟",
                    )
                )
              else:
                results.append(
                    (
                        f"內部單元連結檢查 ({a_tag.text.strip()[:10]}...)",
                        False,
                        f"回應代碼 {sub_res.status_code}",
                    )
                )
                overall_status = "部分連結異常"
                overall_color = "#ffc107"
            except Exception:
              # 略過部分逾時或防爬蟲的次要連結，不強行當作全站掛掉
              pass
            links_checked += 1

  except Exception as e:
    overall_status = "連線失敗 (Down)"
    overall_color = "#dc3545"
    results.append(("首頁可用性 (Homepage)", False, f"連線錯誤: {str(e)}"))

  # 取得台灣時間 (UTC+8)
  now = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=8)
  ).strftime("%Y-%m-%d %H:%M:%S")

  # --- 產生更豐富的 HTML 狀態看板 ---
  items_html = ""
  for name, is_success, desc in results:
    badge_color = "#28a745" if is_success else "#dc3545"
    badge_text = "正常" if is_success else "異常"
    items_html += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 12px; text-align: left; font-weight: bold;">{name}</td>
            <td style="padding: 12px; text-align: center;"><span style="background-color: {badge_color}; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px;">{badge_text}</span></td>
            <td style="padding: 12px; text-align: left; color: #666; font-size: 14px;">{desc}</td>
        </tr>
        """

  html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>機關網站核心功能健康看板</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f4f6f9; color: #333; padding: 40px 20px; }}
        .container {{ max-width: 700px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .overall-badge {{ display: inline-block; padding: 8px 20px; color: white; background-color: {overall_color}; border-radius: 50px; font-weight: bold; font-size: 16px; margin-top: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        .target {{ color: #007bff; text-decoration: none; }}
        .time {{ text-align: center; color: #888; font-size: 13px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🏛️ 機關網站核心功能健康監控看板</h2>
            <p>監控目標：<a href="{BASE_URL}" class="target" target="_blank">{BASE_URL}</a></p>
            <div class="overall-badge">綜合狀態：{overall_status}</div>
        </div>
        <table>
            <thead>
                <tr style="background-color: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                    <th style="padding: 10px; text-align: left;">檢測項目</th>
                    <th style="padding: 10px; text-align: center;">狀態</th>
                    <th style="padding: 10px; text-align: left;">詳細說明</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>
        <div class="time">最後檢測時間（台北時間）：{now}</div>
    </div>
</body>
</html>
"""

  with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
  print("升級版狀態網頁 index.html 產生成功！")


if __name__ == "__main__":
  check_website()
