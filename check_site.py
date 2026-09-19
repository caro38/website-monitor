import datetime
import requests

URL = "https://www.forest.gov.tw/"


def check_website():
  status = "正常 (Operational)"
  color = "#28a745"  # 綠色
  message = "網站運行一切正常，伺服器回應與關鍵內容皆符合預期。"

  try:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(URL, headers=headers, timeout=15)

    if response.status_code != 200:
      status = f"異常 (HTTP Status: {response.status_code})"
      color = "#dc3545"  # 紅色
      message = f"網站回應代碼非 200，狀態碼為: {response.status_code}"
    elif "林業" not in response.text:
      status = "內容異常"
      color = "#ffc107"  # 黃色
      message = (
          "網站可連線，但關鍵字「林業」未出現，可能內容有變或首頁異常。"
      )

  except Exception as e:
    status = "連線失敗 (Down)"
    color = "#dc3545"
    message = f"無法連線至網站，錯誤訊息: {str(e)}"

  # 取得目前台灣時間 (UTC+8)
  now = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=8)
  ).strftime("%Y-%m-%d %H:%M:%S")

  # 產生漂亮的 HTML 看板內容
  html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>網站即時健康監控看板</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f4f6f9; color: #333; text-align: center; padding: 50px 20px; }}
        .card {{ background: white; max-width: 600px; margin: 0 auto; padding: 40px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        .status-badge {{ display: inline-block; padding: 10px 24px; color: white; background-color: {color}; border-radius: 50px; font-weight: bold; font-size: 18px; margin: 20px 0; }}
        .time {{ color: #666; font-size: 14px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px; }}
        .target {{ color: #007bff; text-decoration: none; font-weight: bold; }}
        .message {{ color: #555; margin-top: 15px; font-size: 15px; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>🌐 網站即時健康監控看板</h2>
        <p>監控目標：<a href="{URL}" class="target" target="_blank">{URL}</a></p>
        <div class="status-badge">{status}</div>
        <div class="message">{message}</div>
        <div class="time">最後檢測時間（台北時間）：{now}</div>
    </div>
</body>
</html>
"""

  # 寫入成 index.html 檔案
  with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
  print("狀態網頁 index.html 更新成功！")


if __name__ == "__main__":
  check_website()
