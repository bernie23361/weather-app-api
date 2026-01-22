import requests
import json
import os

def fetch_data():
    # 從環境變數讀取 API Key
    api_key = os.getenv("CWA_API_KEY")
    # 這裡以「今明 36 小時預報」為例
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={api_key}&format=JSON"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        
        # --- 這裡進行資料整理，只留下你 App 版面需要的欄位 ---
        # 假設你只需要「臺中市」
        taichung_data = next(item for item in data['records']['location'] if item['locationName'] == '臺中市')
        
        # 存成你自己的 api.json
        with open("weather_api.json", "w", encoding="utf-8") as f:
            json.dump(taichung_data, f, ensure_ascii=False, indent=4)
        print("資料更新成功！")
    else:
        print("抓取失敗")

if __name__ == "__main__":
    fetch_data()
