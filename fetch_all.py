import requests
import json
import os

def fetch_data():
    # 1. 取得 API Key
    cwa_key = os.getenv("CWA_API_KEY")
    if not cwa_key:
        print("❌ 錯誤: 找不到 CWA_API_KEY，請檢查 GitHub Secrets 設定")
        return

    # 2. 準備 data 資料夾 (如果沒有就建立)
    if not os.path.exists("data"):
        os.makedirs("data")
        print("✅ 已建立 data 資料夾")

    print("🚀 開始抓取氣象署資料...")

    try:
        # 3. 抓取全台鄉鎮預報 (F-D0047-093)
        # 備註：這是一個很大的檔案，包含全台所有鄉鎮
        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-093?Authorization={cwa_key}"
        response = requests.get(url)
        
        # 檢查請求是否成功
        if response.status_code != 200:
            print(f"❌ 請求失敗，狀態碼: {response.status_code}")
            print(response.text)
            return

        data = response.json()
        locations = data['records']['locations'][0]['location']
        
        print(f"📡 成功抓取！共有 {len(locations)} 個鄉鎮資料")

        # 4. 開始拆分檔案
        for loc in locations:
            town_name = loc['locationName'] # 例如：西屯區
            
            # 這裡我們只存簡單的結構，方便 APP 讀取
            simple_data = {
                "town": town_name,
                "data": loc['weatherElement']
            }

            # 存檔：data/西屯區.json
            file_path = f"data/{town_name}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(simple_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 資料拆分完成！已儲存至 data/ 資料夾")

    except Exception as e:
        print(f"❌ 程式執行發生錯誤: {e}")

if __name__ == "__main__":
    fetch_data()
