import requests
import json
import os

# 定義縣市對照表，方便拆分檔案
CITIES = [
    "宜蘭縣", "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣", "臺北市", "新北市", 
    "桃園市", "臺中市", "臺南市", "高雄市", "基隆市", "新竹縣", "新竹市", "苗栗縣", 
    "彰化縣", "南投縣", "雲林縣", "嘉義縣", "嘉義市", "屏東縣"
]

def fetch_all():
    cwa_key = os.getenv("CWA_API_KEY")
    moenv_key = os.getenv("MOENV_API_KEY")
    
    # 建立資料夾存放 API 檔案
    os.makedirs("data", exist_ok=True)

    try:
        # 1. 抓取全台鄉鎮預報 (F-D0047-093) - 這包很大，涵蓋全台 368 鄉鎮
        forecast_url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-093?Authorization={cwa_key}"
        forecast_data = requests.get(forecast_url).json()['records']['locations'][0]['location']

        # 2. 抓取全台空氣品質 (AQI)
        aqi_url = f"https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key={moenv_key}"
        aqi_list = requests.get(aqi_url).json()['records']

        # 3. 抓取地震資訊 (E-A0015-001)
        eq_url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0015-001?Authorization={cwa_key}"
        eq_data = requests.get(eq_url).json()['records']['Earthquake'][0]

        # --- 開始分拆縣市檔案 ---
        for city in CITIES:
            city_json = {
                "city": city,
                "townships": [loc for loc in forecast_data if city in loc.get('locationName', '') or city == loc.get('locationName')],
                "aqi": [station for station in aqi_list if station['county'] == city]
            }
            # 儲存成 data/taichung.json 等
            filename = f"data/{city}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(city_json, f, ensure_ascii=False)

        # --- 儲存全域資訊 (地震、警報) ---
        global_data = {
            "earthquake": eq_data,
            "update_time": forecast_data[0].get('weatherElement', [{}])[0].get('time', [{}])[0].get('startTime', 'N/A')
        }
        with open("data/global.json", "w", encoding="utf-8") as f:
            json.dump(global_data, f, ensure_ascii=False)

        print("✅ 全台資料拆分完畢！")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    fetch_all()
