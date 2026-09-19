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

  # --- 1. 檢查首頁本身 ---
  try:
    res = requests.get(BASE_URL, headers=headers, timeout=15)
    if res.status_code != 200:
      results.append(
          ("首頁可用性 (Homepage)", False, f"狀態碼異常: {res.status_code}")
      )
      overall_status = "首頁異常"
      overall_color = "#dc3545"
    elif "林業" not in res.text:
      results.append(
          ("首頁可用性 (Homepage)", False, "網頁可連線，但關鍵字未出現")
      )
      overall_status = "內容異常"
      overall_color = "#ffc107"
    else:
      results.append(("首頁可用性 (Homepage)", True, "首頁連線正常"))

      # --- 2. 自動提取並檢查第一層連結 (First-tier Links) ---
      soup = BeautifulSoup(res.text, "html.parser")
      unique_links = set()

      # 找出首頁所有超連結
      for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        text = a_tag.text.strip()

        # 過濾條件：排除空白、錨點、電話、信件、外部大型網站
        if (
            not href
            or href.startswith("#")
            or href.startswith("javascript:")
            or href.startswith("tel:")
            or href.startswith("mailto:")
        ):
          continue

        # 組合完整網址
        if href.startswith("/"):
          full_url = BASE_URL.rstrip("/") + href
        elif href.startswith("http"):
          if "forest.gov.tw" not in href:
            continue  # 只檢查同網域的內部第一層連結
          full_url = href
        else:
          continue

        # 去除重複網址與過長的參數，保留乾淨的連結
        clean_url = full_url.split("#")[0]
        if clean_url != BASE_URL and text:
          # 以 (網址, 顯示文字) 存入集合
          unique_links.add((clean_url, text[:15]))

      # 限制最多檢查前 10 個核心第一層連結（避免迴圈跑太久）
      checked_count = 0
      broken_links_count = 0

      for link_url, link_text in list(unique_links)[:10]:
        checked_count += 1
        try:
          # 使用 GET 或 HEAD 測試連結
          sub_res = requests.get(
              link_url, headers=headers, timeout=6, allow_redirects=True
          )
          # 200 正常，或是 3xx 轉址也算活著
          if sub_res.status_code in [200, 301, 302, 303, 307, 308]:
            results.append(
                (f"第一層連結檢查 [{link_text}]", True, f"狀態碼 {sub_res.status_code}")
            )
          else:
            broken_links_count += 1
            results.append(
                (
                    f"第一層連結檢查 [{link_text}]",
                    False,
                    f"失效或異常 (代碼 {sub_res.status_code})",
                )
            )
        except Exception as e:
          broken_links_count += 1
          results.append(
              (f"第一層連結檢查 [{link_text}]", False, f"連線逾時或失敗")
          )

      if broken_links_count > 0:
        overall_status = f"發現 {broken_links_count} 個第一層連結異常"
        overall_color = "#ffc107"  # 黃色警告

  except Exception as e:
    overall_status = "連線失敗 (Down)"
    overall_color = "#dc3545"
    results.append(("首頁可用性 (Homepage)", False, f"連線錯誤: {str(e)}"))

  # 取得台灣時間 (UTC+8)
  now = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=8)
  ).strftime("%Y-%m-%d %H:%M:%S")

  # --- 產生 HTML 看板 ---
  items_html = ""
  for name, is_success, desc in results:
    badge_color = "#28a745" if is_success else "#dc3545"
    badge_text = "正常" if is_success else "失效/異常"
    items_html += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 10px; text-align: left; font-weight: bold; font-size: 13px;">{name}</td>
            <td style="padding: 10px; text-align: center;"><span style="background-color: {badge_color}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">{badge_text}</span></td>
            <td style="padding: 10px; text-align: left; color: #666; font-size: 13px;">{desc}</td>
        </tr>
        """

  html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>機關網站第一層連結巡檢看板</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f4f6f9; color: #333; padding: 30px 15px; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        .header {{ text-align: center; margin-bottom: 25px; }}
        .overall-badge {{ display: inline-block; padding: 6px 18px; color: white; background-color: {overall_color}; border-radius: 50px; font-weight: bold; font-size: 15px; margin-top: 8px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        .target {{ color: #007bff; text-decoration: none; }}
        .time {{ text-align: center; color: #888; font-size: 12px; margin-top: 25px; border-top: 1px solid #eee; padding-top: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🔗 機關網站第一層連結自動巡檢看板</h2>
            <p>監控目標：<a href="{BASE_URL}" class="target" target="_blank">{BASE_URL}</a></p>
            <div class="overall-badge">檢測結果：{overall_status}</div>
        </div>
        <table>
            <thead>
                <tr style="background-color: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                    <th style="padding: 10px; text-align: left; font-size: 13px;">巡檢項目與選單名稱</th>
                    <th style="padding: 10px; text-align: center; font-size: 13px;">狀態</th>
                    <th style="padding: 10px; text-align: left; font-size: 13px;">檢測詳情</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>
        <div class="time">最後巡檢時間（台北時間）：{now}</div>
    </div>
</body>
</html>
"""

  with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
  print("第一層連結巡檢網頁產生成功！")


if __name__ == "__main__":
  check_website()
