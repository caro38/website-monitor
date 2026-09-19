import os
import requests

URL = "https://www.forest.gov.tw/"

def check_website():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(URL, headers=headers, timeout=15)

        # 1. 檢查 HTTP 狀態碼
        if response.status_code != 200:
            raise Exception(f"網站回應異常，狀態碼: {response.status_code}")

        # 2. 檢查關鍵字
        if "林業" not in response.text:
            raise Exception("網頁內容異常：找不到關鍵字「林業」")

        print("【成功】林業保育署網站首頁運行正常！")

    except Exception as e:
        error_msg = f"【網站檢測失敗警報】\n目標網址: {URL}\n錯誤原因: {str(e)}"
        print(error_msg)
        exit(1)

if __name__ == "__main__":
    check_website()
