import requests
import json
import os
import time

def fetch_data():
    cwa_key = os.getenv("CWA_API_KEY")
    if not cwa_key:
        print("❌ 錯誤: 找不到 CWA_API_KEY")
        return

    # 建立 data 資料夾
    if not os.path.exists("data"):
        os.makedirs("data")

    # 氣象署縣市預報 API 代號
    county_api_list = {
        "宜蘭縣": "F-D0047-001", "桃園市": "F-D0047-005", "新竹縣": "F-D0047-009",
        "苗栗縣": "F-D0047-013", "彰化縣": "F-D0047-017", "南投縣": "F-D0047-021",
        "雲林縣": "F-D0047-025", "嘉義縣": "F-D0047-029", "屏東縣": "F-D0047-033",
        "臺東縣": "F-D0047-037", "花蓮縣": "F-D0047-041", "澎湖縣": "F-D0047-045",
        "基隆市": "F-D0047-049", "新竹市": "F-D0047-053", "嘉義市": "F-D0047-057",
        "臺北市": "F-D0047-061", "高雄市": "F-D0047-065", "新北市": "F-D0047-069",
        "臺中市": "F-D0047-073", "臺南市": "F-D0047-077", "連江縣": "F-D0047-081",
        "金門縣": "F-D0047-085"
    }

    print("🚀 開始分縣市抓取氣象署資料 (終極相容版)...")
    success_count = 0

    for city_name, api_id in county_api_list.items():
        try:
            url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{api_id}?Authorization={cwa_key}&format=JSON"
            res = requests.get(url)
            
            if res.status_code != 200:
                print(f"⚠️ {city_name} 抓取失敗 (Status: {res.status_code})")
                continue

            data = res.json()
            records = data.get('records', {})
            locations_raw = []

            # --- 🔍 智慧偵測資料結構 (修正重點) ---
            # 情況 1: 小寫 locations -> location (舊版)
            if 'locations' in records:
                locations_raw = records['locations'][0]['location']
            
            # 情況 2: 大寫 Locations -> Location (新版，就是你遇到的情況)
            elif 'Locations' in records:
                locations_raw = records['Locations'][0]['Location']
                
            # 情況 3: 直接是 location
            elif 'location' in records:
                locations_raw = records['location']
            
            else:
                print(f"❌ {city_name} 結構異常，現有欄位: {list(records.keys())}")
                continue
            
            # --- 開始拆解鄉鎮 ---
            count = 0
            for loc in locations_raw:
                town_name = loc.get('locationName', loc.get('LocationName', '未知'))
                
                # 取得天氣因子 (兼顧大小寫)
                weather_elements = loc.get('weatherElement', loc.get('WeatherElement', []))

                processed_data = {
                    "city": city_name,
                    "district": town_name,
                    "data": weather_elements,
                    "update_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }

                file_path = f"data/{town_name}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(processed_data, f, ensure_ascii=False)
                count += 1
            
            print(f"✅ {city_name} 處理完成！(共 {count} 個鄉鎮)")
            success_count += 1
            
        except Exception as e:
            print(f"❌ {city_name} 發生錯誤: {e}")

    print(f"\n🎉 執行結束！成功處理 {success_count} 個縣市。")

if __name__ == "__main__":
    fetch_data()
