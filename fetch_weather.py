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

# --- 🧠 生活指數計算 (已修復大小寫崩潰問題) ---
def calculate_lifestyle_indices(weather_elements, current_vals):
    curr_t = current_vals.get('temp', 25)
    curr_rh = current_vals.get('humidity', 75)
    curr_ws = current_vals.get('wind_speed', 2)
    curr_rain = current_vals.get('rain', 0)
    
    # 預報趨勢 (未來 12h 降雨機率)
    pop_12h = 0
    for item in weather_elements:
        # ⚠️ 這裡就是之前報錯的地方，現在加上了 get 防呆
        e_name = item.get('elementName', item.get('ElementName'))
        
        if e_name == 'PoP12h':
            # 同樣加上時間與數值的防呆
            time_list = item.get('time', item.get('Time', []))
            if time_list:
                e_vals = time_list[0].get('elementValue', time_list[0].get('ElementValue', []))
                if e_vals:
                    val = e_vals[0].get('value', e_vals[0].get('Value', '0'))
                    try:
                        pop_12h = int(val)
                    except:
                        pop_12h = 0

    # 體感溫度估算
    curr_at = curr_t + 0.33 * curr_rh / 100 * 6.105 * 2.718 ** (17.27 * curr_t / (237.7 + curr_t)) - 4

    # 1. 👕 穿衣
    if curr_t < 15: clothing = "厚外套"
    elif 15 <= curr_t < 20: clothing = "夾克/風衣"
    elif 20 <= curr_t < 26: clothing = "短袖+薄外套"
    else: clothing = "透氣短袖"

    # 2. 🚲 騎車
    if curr_rain > 0 or pop_12h > 40: cycling = "不建議"
    elif curr_ws > 5: cycling = "需防風"
    else: cycling = "非常適宜"

    # 3. 🚗 洗車
    if pop_12h > 30: car_wash = "不宜"
    else: car_wash = "適宜"

    # 4. ☀️ 曬衣
    if curr_rain > 0 or curr_rh > 85: laundry = "不宜"
    else: laundry = "適宜"

    # 5. 🛡️ 防曬
    sunscreen = "中" if curr_t > 25 else "弱"

    # 6. ✨ 保養
    skincare = "重保濕" if curr_rh < 50 else "控油清爽"

    # 7. 🩺 感冒
    cold_risk = "注意保暖" if curr_t < 16 else "低風險"

    # 8. 🐕 寵物
    dog_walk = "不推薦" if curr_rain > 0 else "推薦"

    # 9. 🏃 運動
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
            # 檢查 records 是否存在
            records = res_aqi.get('records', [])
            for record in records:
                county = record.get('county')
                aqi_val = record.get('aqi')
                if county and aqi_val:
                    aqi_map[county] = int(aqi_val)
        print("✅ AQI 完成")
    except Exception as e:
        print(f"⚠️ AQI 部分略過: {e}")

    # --- 2. 抓取 真實觀測 (建立有效測站資料庫) ---
    valid_stations = [] 
    
    try:
        url_obs = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001?Authorization={cwa_key}&format=JSON"
        res_obs = requests.get(url_obs).json()
        stations = res_obs['records']['Station']
        
        count_valid = 0
        for st in stations:
            geo = st['GeoInfo']
            lat = float(geo['Coordinates'][0]['StationLatitude'])
            lon = float(geo['Coordinates'][0]['StationLongitude'])
            location_name = f"{geo['CountyName']}{geo['TownName']}" 
            station_name = st['StationName']

            weather = st['WeatherElement']
            try:
                temp = float(weather['AirTemperature'])
                # 過濾故障 (-99)
                if temp > -50: 
                    humid = float(weather['RelativeHumidity'])
                    wind = float(weather['WindSpeed'])
                    rain = float(weather['Now']['Precipitation'])
                    
                    if humid < 0: humid = 75
                    if wind < 0: wind = 0
                    if rain < 0: rain = 0

                    valid_stations.append({
                        "name": station_name,
                        "town_key": location_name,
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

    # --- 3. 處理 368 鄉鎮 ---
    county_api_week = {
        "宜蘭縣": "F-D0047-003", "桃園市": "F-D0047-007", "新竹縣": "F-D0047-009",
        "苗栗縣": "F-D0047-013", "彰化縣": "F-D0047-017", "南投縣": "F-D0047-021",
        "雲林縣": "F-D0047-025", "嘉義縣": "F-D0047-029", "屏東縣": "F-D0047-033",
        "臺東縣": "F-D0047-037", "花蓮縣": "F-D0047-041", "澎湖縣": "F-D0047-045",
        "基隆市": "F-D0047-049", "新竹市": "F-D0047-053", "嘉義市": "F-D0047-057",
        "臺北市": "F-D0047-061", "高雄市": "F-D0047-065", "新北市": "F-D0047-069",
        "臺中市": "F-D0047-073", "臺南市": "F-D0047-077", "連江縣": "F-D0047-081",
        "金門縣": "F-D0047-085"
    }

    print("📡 開始配對：尋找最近測站...")
    
    for city_name, api_id in county_api_week.items():
        try:
            url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{api_id}?Authorization={cwa_key}&format=JSON"
            res = requests.get(url)
            data = res.json()
            
            records = data.get('records', {})
            locations_raw = []
            if 'locations' in records: locations_raw = records['locations'][0]['location']
            elif 'Locations' in records: locations_raw = records['Locations'][0]['Location']
            elif 'location' in records: locations_raw = records['location']
            
            for loc in locations_raw:
                town_name = loc.get('locationName', loc.get('LocationName', '未知'))
                weather_elements = loc.get('weatherElement', loc.get('WeatherElement', []))
                
                town_lat = float(loc.get('lat', 25.0))
                town_lon = float(loc.get('lon', 121.5))
                
                # === 核心：尋找最近測站 ===
                matched_station = None
                min_dist = 99999.0
                
                for st in valid_stations:
                    dist = calculate_distance(town_lat, town_lon, st['lat'], st['lon'])
                    if dist < min_dist:
                        min_dist = dist
                        matched_station = st

                final_obs_data = None
                source_station_name = ""

                # 距離 < 15km 才採用
                if matched_station and min_dist < 15:
                    final_obs_data = matched_station['data']
                    source_station_name = matched_station['name']
                
                # 解析預報 (備案 & 未來)
                forecast_temp = "25"
                forecast_wx = "多雲"
                daily_forecast = []
                processed_dates = set()

                for el in weather_elements:
                    e_name = el.get('elementName', el.get('ElementName'))
                    time_list = el.get('time', el.get('Time', []))
                    
                    if e_name == 'T' and time_list: 
                        vals = time_list[0].get('elementValue', time_list[0].get('ElementValue', []))
                        if vals: forecast_temp = vals[0].get('value', '25')
                    
                    if e_name == 'Wx' and time_list:
                        vals = time_list[0].get('elementValue', time_list[0].get('ElementValue', []))
                        if vals: forecast_wx = vals[0].get('value', '多雲')

                    if e_name == 'T' and time_list:
                        for t in time_list:
                            start_time = t.get('startTime', t.get('StartTime', ''))
                            vals = t.get('elementValue', t.get('ElementValue', []))
                            if not vals: continue
                            val = vals[0].get('value', '0')

                            if len(start_time) >= 10:
                                dt = datetime.strptime(start_time[:10], "%Y-%m-%d")
                                date_str = dt.strftime("%m/%d")
                                if "06:00" in start_time or "12:00" in start_time:
                                    if date_str not in processed_dates:
                                        daily_forecast.append({"day": date_str, "temp": val, "condition": "多雲"})
                                        processed_dates.add(date_str)

                # 最終數據整合
                if final_obs_data:
                    final_temp = final_obs_data['temp']
                    final_rain = final_obs_data['rain']
                    final_wx = "雨天" if final_rain > 0 else forecast_wx 
                else:
                    final_temp = int(forecast_temp)
                    final_rain = 0
                    final_wx = forecast_wx
                    final_obs_data = {"temp": final_temp, "humidity": 75, "wind_speed": 2, "rain": 0}
                    source_station_name = "預報推算"

                indices = calculate_lifestyle_indices(weather_elements, final_obs_data)
                my_aqi = aqi_map.get(city_name, 35)

                processed_data = {
                    "city": city_name,
                    "district": town_name,
                    "temp": str(int(final_temp)),
                    "apparent_temp": str(int(final_temp - 2)),
                    "weather": final_wx,
                    "aqi": my_aqi,
                    "station_source": source_station_name,
                    "suggestions": indices,
                    "daily_forecast": daily_forecast[:7],
                    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                file_path = f"data/{town_name}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(processed_data, f, ensure_ascii=False)
            
            print(f"✅ {city_name} 完成")
            
        except Exception as e:
            # 印出更多細節幫助除錯
            print(f"❌ {city_name} 錯誤: {e}")
            import traceback
            traceback.print_exc()

    print("🎉 全台氣象資料更新完畢 (含空間替補)！")

if __name__ == "__main__":
    fetch_data()
