import datetime
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.forest.gov.tw/"


def check_website():
  results = []
  overall_status = "全面正常 (Operational)"
  overall_color = "#28a745"  # 綠色
  anomaly_count = 0

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }

  try:
    # --- 1. 檢查首頁可用性 ---
    res = requests.get(BASE_URL, headers=headers, timeout=15)
    if res.status_code != 200:
      results.append(
          ("首頁可用性 (Homepage)", False, f"狀態碼異常: {res.status_code}")
      )
      anomaly_count += 1
    elif "林業" not in res.text:
      results.append(
          ("首頁可用性 (Homepage)", False, "網頁可連線，但關鍵字未出現")
      )
      anomaly_count += 1
    else:
      results.append(("首頁可用性 (Homepage)", True, "首頁連線正常，關鍵字吻合"))

      soup = BeautifulSoup(res.text, "html.parser")

      # ==========================================
      # 項目 1：核心次選單與子系統連結有效性
      # ==========================================
      menu_links = set()
      for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        text = a_tag.text.strip()
        # 尋找導覽列或主要區塊連結
        if href and not href.startswith(("#", "javascript:", "tel:", "mailto:")):
          if href.startswith("/"):
            full_url = BASE_URL.rstrip("/") + href
          elif "forest.gov.tw" in href:
            full_url = href
          else:
            continue

          clean_url = full_url.split("#")[0]
          if clean_url != BASE_URL and len(text) > 1:
            menu_links.add((clean_url, text[:12]))

      # 抽樣檢查前 4 個核心導覽連結
      menu_checked = 0
      for link_url, link_text in list(menu_links)[:4]:
        menu_checked += 1
        try:
          sub_res = requests.get(
              link_url, headers=headers, timeout=5, allow_redirects=True
          )
          if sub_res.status_code in [200, 301, 302, 307, 308]:
            results.append(
                (f"次選單連結 [{link_text}]", True, f"狀態碼 {sub_res.status_code}")
            )
          else:
            results.append(
                (
                    f"次選單連結 [{link_text}]",
                    False,
                    f"回應代碼 {sub_res.status_code}",
                )
            )
            anomaly_count += 1
        except Exception:
          results.append((f"次選單連結 [{link_text}]", False, "連線逾時或失敗"))
          anomaly_count += 1

      # ==========================================
      # 項目 2：最新公告與下載附件狀態檢測
      # ==========================================
      # 尋找最新消息或公告區塊的連結
      news_links = []
      for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        text = a_tag.text.strip()
        # 依據常見機關網站公告網址特徵或文字過濾
        if (
            ("news" in href or "bulletin" in href or "cp.aspx" in href)
            and len(text) > 4
            and not href.startswith("#")
        ):
          full_url = (
              BASE_URL.rstrip("/") + href if href.startswith("/") else href
          )
          if full_url not in [n[0] for n in news_links]:
            news_links.append((full_url, text[:15]))

      # 檢查前 3 筆最新公告
      news_checked = 0
      for news_url, news_title in news_links[:3]:
        news_checked += 1
        try:
          news_res = requests.get(news_url, headers=headers, timeout=6)
          if news_res.status_code == 200:
            # 進一步檢查該公告頁面是否包含附件檔案 (例如 .pdf, .odf, .doc)
            news_soup = BeautifulSoup(news_res.text, "html.parser")
            has_attachment = False
            for file_a in news_soup.find_all("a", href=True):
              file_href = file_a["href"].lower()
              if any(
                  ext in file_href for ext in [".pdf", ".odf", ".doc", ".odt"]
              ):
                has_attachment = True
                break

            att_status = (
                "公告正常，內含有效附件"
                if has_attachment
                else "公告正常（無附件）"
            )
            results.append((f"最新公告檢測 [{news_title}...]", True, att_status))
          else:
            results.append(
                (
                    f"最新公告檢測 [{news_title}...]",
                    False,
                    f"公告頁面失效 ({news_res.status_code})",
                )
            )
            anomaly_count += 1
        except Exception:
          results.append(
              (f"最新公告檢測 [{news_title}...]", False, "公告頁面連線逾時")
          )
          anomaly_count += 1

      # 如果首頁沒抓到明顯的公告結構，補一個基本檢測項
      if news_checked == 0:
        results.append(
            ("最新公告與附件檢測", True, "首頁未直接抓取到公告結構，略過細節")
        )

      # ==========================================
      # 項目 3：站內搜尋功能可用性 (Search Check)
      # ==========================================
      search_keyword = "步道"
      search_url = f"{BASE_URL.rstrip('/')}/search?q={search_keyword}"
      try:
        search_res = requests.get(search_url, headers=headers, timeout=8)
        # 只要伺服器正常回應 200，且頁面有內容，代表搜尋引擎/資料庫存活
        if search_res.status_code == 200 and len(search_res.text) > 500:
          results.append(
              (
                  f"站內搜尋功能 (關鍵字：「{search_keyword}」)",
                  True,
                  "搜尋引擎回應正常，資料庫運作中",
              )
          )
        else:
          results.append(
              (
                  f"站內搜尋功能 (關鍵字：「{search_keyword}」)",
                  False,
                  f"搜尋回應異常 (狀態碼 {search_res.status_code})",
              )
          )
          anomaly_count += 1
      except Exception:
        results.append(
            (
                f"站內搜尋功能 (關鍵字：「{search_keyword}」)",
                False,
                "搜尋模組連線逾時",
            )
        )
        anomaly_count += 1

  except Exception as e:
    overall_status = "系統嚴重異常 (Down)"
    overall_color = "#dc3545"
    results.append(("整體系統連線", False, f"發生重大錯誤: {str(e)}"))
    anomaly_count += 99

  # 結算綜合狀態
  if anomaly_count > 0:
    overall_status = f"發現 {anomaly_count} 項異常或警報"
    overall_color = "#ffc107" if anomaly_count < 3 else "#dc3545"

  # 取得台灣時間 (UTC+8)
  now = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=8)
  ).strftime("%Y-%m-%d %H:%M:%S")

  # --- 產生 HTML 呈現看板 ---
  items_html = ""
  for name, is_success, desc in results:
    badge_color = "#28a745" if is_success else "#dc3545"
    badge_text = "正常" if is_success else "異常/失效"
    items_html += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 12px; text-align: left; font-weight: bold; font-size: 13px;">{name}</td>
            <td style="padding: 12px; text-align: center;"><span style="background-color: {badge_color}; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px;">{badge_text}</span></td>
            <td style="padding: 12px; text-align: left; color: #555; font-size: 13px;">{desc}</td>
        </tr>
        """

  html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>機關網站全方位巡檢看板</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f4f6f9; color: #333; padding: 30px 15px; }}
        .container {{ max-width: 850px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        .header {{ text-align: center; margin-bottom: 25px; }}
        .overall-badge {{ display: inline-block; padding: 8px 22px; color: white; background-color: {overall_color}; border-radius: 50px; font-weight: bold; font-size: 16px; margin-top: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        .target {{ color: #007bff; text-decoration: none; }}
        .time {{ text-align: center; color: #888; font-size: 13px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🏛️ 機關網站核心功能全方位巡檢看板</h2>
            <p>監控目標：<a href="{BASE_URL}" class="target" target="_blank">{BASE_URL}</a></p>
            <div class="overall-badge">綜合檢測結果：{overall_status}</div>
        </div>
        <table>
            <thead>
                <tr style="background-color: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                    <th style="padding: 12px; text-align: left; font-size: 13px;">巡檢模組與功能項目</th>
                    <th style="padding: 12px; text-align: center; font-size: 13px;">狀態</th>
                    <th style="padding: 12px; text-align: left; font-size: 13px;">檢測詳情與說明</th>
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
  print("全方位巡檢看板 index.html 產生成功！")


if __name__ == "__main__":
  check_website()
