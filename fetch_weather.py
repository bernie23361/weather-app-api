import requests
import json
import os
import time
import math
from datetime import datetime

# --- 📐 數學小教室：計算地球兩點距離 (Haversine 公式) ---
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # 地球半徑 (公里)
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c # 回傳距離 (km)

# --- 🧠 生活指數計算 (維持不變) ---
def calculate_lifestyle_indices(weather_elements, current_vals):
    curr_t = current_vals.get('temp', 25)
    curr_rh = current_vals.get('humidity', 75)
    curr_ws = current_vals.get('wind_speed', 2)
    curr_rain = current_vals.get('rain', 0)
    
    # 預報趨勢
    pop_12h = 0
    for item in weather_elements:
        if item['elementName'] == 'PoP12h':
            pop_12h = int(item['time'][0]['elementValue'][0]['value']) if item['time'] else 0

    curr_at = curr_t + 0.33 * curr_rh / 100 * 6.105 * 2.718 ** (17.27 * curr_t / (237.7 + curr_t)) - 4

    if curr_t < 15: clothing = "厚外套"
    elif 15 <= curr_t < 20: clothing = "夾克/風衣"
    elif 20 <= curr_t < 26: clothing = "短袖+薄外套"
    else: clothing = "透氣短袖"

    if curr_rain > 0 or pop_12h > 40: cycling = "不建議"
    elif curr_ws > 5: cycling = "需防風"
    else: cycling = "非常適宜"

    if pop_12h > 30: car_wash = "不宜"
    else: car_wash = "適宜"

    if curr_rain > 0 or curr_rh > 85: laundry = "不宜"
    else: laundry = "適宜"

    sunscreen = "中" if curr_t > 25 else "弱"
    skincare = "重保濕" if curr_rh < 50 else "控油清爽"
    cold_risk = "注意保暖" if curr_t < 16 else "低風險"
    dog_walk = "不推薦" if curr_rain > 0 else "推薦"
    sport = "室內佳" if curr_rain > 0 else "戶外佳"

    return {
        "clothing": clothing, "cycling": cycling, "sunscreen": sunscreen,
        "laundry": laundry, "car_wash": car_wash, "skincare": skincare,
        "cold_risk": cold_risk, "dog_walk": dog_walk, "sport": sport
    }

def fetch_data():
    cwa_key = os.getenv("CWA_API_KEY")
    moenv_key = os.getenv("MOENV_API_KEY")

    if not os.path.exists("data"):
        os.makedirs("data")

    print("🚀 啟動氣象站：觀測資料 (含距離替補機制)...")

    # --- 1. 抓取 AQI ---
    aqi_map = {}
    try:
        if moenv_key:
            url_aqi = f"https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key={moenv_key}"
            res_aqi = requests.get(url_aqi).json()
            for record in res_aqi['records']:
                county = record['county']
                aqi_val = record['aqi']
                if county not in aqi_map:
                    aqi_map[county] = int(aqi_val) if aqi_val else 0
        print("✅ AQI 完成")
    except:
        print("⚠️ AQI 失敗")

    # --- 2. 抓取 真實觀測 (建立有效測站資料庫) ---
    valid_stations = [] # 存列表，方便算距離: [{lat, lon, data...}]
    
    try:
        url_obs = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001?Authorization={cwa_key}&format=JSON"
        res_obs = requests.get(url_obs).json()
        stations = res_obs['records']['Station']
        
        count_valid = 0
        for st in stations:
            geo = st['GeoInfo']
            lat = float(geo['Coordinates'][0]['StationLatitude'])
            lon = float(geo['Coordinates'][0]['StationLongitude'])
            location_name = f"{geo['CountyName']}{geo['TownName']}" # 例如: 臺南市佳里區
            station_name = st['StationName']

            # 提取並檢查數據是否故障 (-99)
            weather = st['WeatherElement']
            try:
                temp = float(weather['AirTemperature'])
                # 只有當溫度正常 (> -50) 且不是故障代碼時才算「有效測站」
                if temp > -50: 
                    humid = float(weather['RelativeHumidity'])
                    wind = float(weather['WindSpeed'])
                    rain = float(weather['Now']['Precipitation'])
                    
                    # 修復極端值
                    if humid < 0: humid = 75
                    if wind < 0: wind = 0
                    if rain < 0: rain = 0

                    valid_stations.append({
                        "name": station_name,
                        "town_key": location_name, # 用來做直接對應
                        "lat": lat,
                        "lon": lon,
                        "data": {
                            "temp": temp,
                            "humidity": humid,
                            "wind_speed": wind,
                            "rain": rain
                        }
                    })
                    count_valid += 1
            except:
                continue
                
        print(f"✅ 有效觀測站建立完成 (共 {count_valid} 個運作中)")

    except Exception as e:
        print(f"❌ 觀測資料失敗: {e}")

    # --- 3. 處理 368 鄉鎮 (分縣市處理以免記憶體爆掉) ---
    county_api_week = {
        "宜蘭縣": "F-D0047-003", "桃園市": "F-D0047-007", "新竹縣": "F-D0047-011",
        "苗栗縣": "F-D0047-015", "彰化縣": "F-D0047-019", "南投縣": "F-D0047-023",
        "雲林縣": "F-D0047-027", "嘉義縣": "F-D0047-031", "屏東縣": "F-D0047-035",
        "臺東縣": "F-D0047-039", "花蓮縣": "F-D0047-043", "澎湖縣": "F-D0047-047",
        "基隆市": "F-D0047-051", "新竹市": "F-D0047-055", "嘉義市": "F-D0047-059",
        "臺北市": "F-D0047-063", "高雄市": "F-D0047-067", "新北市": "F-D0047-071",
        "臺中市": "F-D0047-075", "臺南市": "F-D0047-079", "連江縣": "F-D0047-083",
        "金門縣": "F-D0047-087"
    }

    print("📡 開始配對：尋找最近測站...")
    
    for city_name, api_id in county_api_week.items():
        try:
            url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{api_id}?Authorization={cwa_key}&format=JSON"
            res = requests.get(url)
            data = res.json()
            
            # 結構判容
            records = data.get('records', {})
            locations_raw = []
            if 'locations' in records: locations_raw = records['locations'][0]['location']
            elif 'Locations' in records: locations_raw = records['Locations'][0]['Location']
            elif 'location' in records: locations_raw = records['location']
            
            for loc in locations_raw:
                town_name = loc.get('locationName', loc.get('LocationName', '未知'))
                weather_elements = loc.get('weatherElement', loc.get('WeatherElement', []))
                
                # 取得該鄉鎮的經緯度 (Forecast API 裡面有!)
                town_lat = float(loc.get('lat', 25.0))
                town_lon = float(loc.get('lon', 121.5))
                
                # === 🕵️‍♂️ 核心邏輯：尋找數據 ===
                target_key = f"{city_name}{town_name}"
                
                # 策略 1: 嘗試找「同名且同縣市」的站，而且要在有效清單裡
                # (這會自動過濾掉 -99 的站，因為 -99 根本沒進 valid_stations)
                matched_station = None
                min_dist = 99999.0
                
                # 先找名字完全一樣的 (例如: 臺南市麻豆區 -> 站名: 麻豆)
                # 但因為站名有時不對應，我們直接用「距離」來決定最公平！
                # 這樣麻豆如果故障，程式自動會算距離，發現佳里最近，就抓佳里。
                
                final_obs_data = None
                source_station_name = ""

                # 遍歷所有有效測站，找最近的
                for st in valid_stations:
                    dist = calculate_distance(town_lat, town_lon, st['lat'], st['lon'])
                    if dist < min_dist:
                        min_dist = dist
                        matched_station = st

                # 如果最近的站距離 < 15公里，我們就採信它 (太遠代表該地真的沒資料，只好用預報)
                if matched_station and min_dist < 15:
                    final_obs_data = matched_station['data']
                    source_station_name = matched_station['name']
                
                # --- 資料整合 ---
                # 解析預報 (作為備案 & 未來趨勢)
                forecast_temp = "25"
                forecast_wx = "多雲"
                daily_forecast = []
                processed_dates = set()

                for el in weather_elements:
                    e_name = el.get('elementName', el.get('ElementName'))
                    time_list = el.get('time', el.get('Time', []))
                    
                    if e_name == 'T' and time_list: forecast_temp = time_list[0].get('elementValue')[0].get('value')
                    if e_name == 'Wx' and time_list: forecast_wx = time_list[0].get('elementValue')[0].get('value')

                    if e_name == 'T':
                        for t in time_list:
                            start_time = t.get('startTime')
                            val = t.get('elementValue')[0].get('value')
                            dt = datetime.strptime(start_time[:10], "%Y-%m-%d")
                            date_str = dt.strftime("%m/%d")
                            if "06:00" in start_time or "12:00" in start_time:
                                if date_str not in processed_dates:
                                    daily_forecast.append({"day": date_str, "temp": val, "condition": "多雲"})
                                    processed_dates.add(date_str)

                # 決定最終顯示數據
                if final_obs_data:
                    final_temp = final_obs_data['temp']
                    final_rain = final_obs_data['rain']
                    # 如果觀測到有雨，就顯示雨天，否則用預報的描述
                    final_wx = "雨天" if final_rain > 0 else forecast_wx 
                else:
                    # 真的太偏僻，連最近的站都超過 15km (例如高山或外島死角)，用預報
                    final_temp = int(forecast_temp)
                    final_rain = 0
                    final_wx = forecast_wx
                    final_obs_data = {"temp": final_temp, "humidity": 75, "wind_speed": 2, "rain": 0}
                    source_station_name = "預報推算"

                # 計算生活指數
                indices = calculate_lifestyle_indices(weather_elements, final_obs_data)
                my_aqi = aqi_map.get(city_name, 35)

                processed_data = {
                    "city": city_name,
                    "district": town_name,
                    "temp": str(int(final_temp)),
                    "apparent_temp": str(int(final_temp - 2)), # 簡單模擬
                    "weather": final_wx,
                    "aqi": my_aqi,
                    "station_source": source_station_name, # 讓你知道是抓哪個站
                    "suggestions": indices,
                    "daily_forecast": daily_forecast[:7],
                    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                file_path = f"data/{town_name}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(processed_data, f, ensure_ascii=False)
            
            print(f"✅ {city_name} 完成")
            
        except Exception as e:
            print(f"❌ {city_name} 錯誤: {e}")

    print("🎉 全台氣象資料更新完畢 (含空間替補)！")

if __name__ == "__main__":
    fetch_data()
