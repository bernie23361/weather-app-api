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

    # 氣象署「未來 2 天預報」的各縣市 API 代號列表 (絕對穩定版)
    # 格式: 縣市名稱 -> API ID
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

    print("🚀 開始分縣市抓取氣象署資料...")

    success_count = 0

    for city_name, api_id in county_api_list.items():
        try:
            # 1. 抓取該縣市資料
            url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{api_id}?Authorization={cwa_key}"
            res = requests.get(url)
            
            if res.status_code != 200:
                print(f"⚠️ {city_name} 抓取失敗 (Status: {res.status_code})")
                continue

            data = res.json()
            locations = data['records']['locations'][0]['location']
            
            # 2. 拆解成該縣市底下的所有鄉鎮
            for loc in locations:
                town_name = loc['locationName'] # 例如：西屯區、信義區
                
                # 簡單整理一下資料，縮小體積
                weather_elements = loc['weatherElement']
                
                # 製作簡化版 JSON
                processed_data = {
                    "city": city_name,
                    "district": town_name,
                    "data": weather_elements, # 這裡保留了完整未來2天預報
                    "update_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }

                # 存檔 -> data/西屯區.json
                # 注意：如果不同縣市有同名鄉鎮(如仁愛區)，可能會覆蓋，建議加上縣市前綴
                # 但為了你方便，我們先直接存鄉鎮名
                file_path = f"data/{town_name}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(processed_data, f, ensure_ascii=False)
            
            print(f"✅ {city_name} 處理完成！")
            success_count += 1
            
        except Exception as e:
            print(f"❌ {city_name} 發生錯誤: {e}")

    print(f"\n🎉 全部完成！共處理 {success_count} 個縣市的資料。")

if __name__ == "__main__":
    fetch_data()
