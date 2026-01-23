import requests
import json
import os
import time
from datetime import datetime, timedelta

def get_taiwanese_quote(apparent_temp, weather, is_raining, wind_speed, is_broken=False):
    # 如果測站故障，直接回傳故障訊息
    if is_broken:
        return "⚠️ 該鄉鎮目前無測站訊號或儀器維護中。"

    advice = "天氣剛剛好，出門走走吧！" 
    if is_raining:
        if "大雨" in weather or "豪雨" in weather:
            advice = "外面落大雨，雨具要傳賀 (準備好)，騎車卡注意安全喔！"
        else:
            advice = "外面在飄雨，出門記得帶把傘，走路小心滑倒。"
    elif wind_speed > 8:
        advice = "風透透 (風很大)，騎車容易飄，記得戴個帽子防風喔。"
    elif apparent_temp < 15:
        advice = "天氣冷吱吱，寒流發威，出門愛穿乎燒喔！"
    elif 15 <= apparent_temp < 21:
        advice = "風吹來涼涼的，日夜溫差大，出門記得帶件薄外套。"
    elif 21 <= apparent_temp < 27:
        advice = "天氣很速西 (舒適)，微風徐徐，超適合出門散散步！"
    elif 27 <= apparent_temp < 32:
        advice = "天氣有點悶熱，透氣短袖穿起來，記得多喝水。"
    else: 
        advice = "日頭赤炎炎，超級熱！防曬做好小心中暑，盡量待在冷氣房！"
    return advice

def calculate_lifestyle_indices(weather_elements, current_vals, is_broken=False):
    # 如果測站故障，生活指數無法計算，回傳預設空值
    if is_broken:
        return {
            "clothing": "--", "cycling": "--", "sunscreen": "--",
            "laundry": "--", "car_wash": "--", "skincare": "--",
            "cold_risk": "--", "dog_walk": "--", "sport": "--",
            "apparent_temp": "--" 
        }

    curr_t = current_vals.get('temp', 25)
    curr_rh = current_vals.get('humidity', 75)
    curr_ws = current_vals.get('wind_speed', 2)
    curr_rain = current_vals.get('rain', 0)
    
    pop_12h = 0
    for item in weather_elements:
        e_name = item.get('elementName', item.get('ElementName'))
        if e_name == 'PoP12h':
            time_list = item.get('time', item.get('Time', []))
            if time_list:
                e_vals = time_list[0].get('elementValue', time_list[0].get('ElementValue', []))
                if e_vals:
                    val = e_vals[0].get('value', e_vals[0].get('Value', '0'))
                    try: pop_12h = int(val)
                    except: pop_12h = 0

    curr_at = curr_t + 0.33 * curr_rh / 100 * 6.105 * 2.718 ** (17.27 * curr_t / (237.7 + curr_t)) - 4
    curr_at = round(curr_at)

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
        "cold_risk": cold_risk, "dog_walk": dog_walk, "sport": sport,
        "apparent_temp": curr_at 
    }

def fetch_data():
    cwa_key = os.getenv("CWA_API_KEY")
    moenv_key = os.getenv("MOENV_API_KEY")

    if not os.path.exists("data"):
        os.makedirs("data")

    tw_now = datetime.utcnow() + timedelta(hours=8)
    tw_now_str = tw_now.strftime("%Y-%m-%d %H:%M:%S")

    print(f"🚀 啟動氣象站: 台灣時間 {tw_now_str}")

    aqi_map = {}
    try:
        if moenv_key:
            url_aqi = f"https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key={moenv_key}"
            res_aqi = requests.get(url_aqi).json()
            for record in res_aqi.get('records', []):
                county = record.get('county')
                aqi_val = record.get('aqi')
                if county and aqi_val: aqi_map[county] = int(aqi_val)
        print("✅ AQI 完成")
    except:
        print("⚠️ AQI 失敗 (使用預設值)")

    # ----------------------------------------------------
    # 🎯 絕對精準：建立 O-A0003-001 鄉鎮唯一測站地圖
    # ----------------------------------------------------
    valid_stations_by_town = {}    
    try:
        url_obs = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001?Authorization={cwa_key}&format=JSON"
        res_obs = requests.get(url_obs).json()
        stations = res_obs['records']['Station']
        
        count = 0
        for st in stations:
            obs_time_str = st['ObsTime']['DateTime']
            obs_time = datetime.strptime(obs_time_str[:19], "%Y-%m-%dT%H:%M:%S")
            
            # 嚴格過濾：超過 1.5 小時未更新視同「儀器故障」
            if (tw_now - obs_time).total_seconds() > 5400:
                continue 

            geo = st['GeoInfo']
            county_name = geo['CountyName']
            town_name = geo['TownName']
            full_town_key = f"{county_name}{town_name}" # 例如：花蓮縣秀林鄉

            station_name = st['StationName']
            weather = st['WeatherElement']
            
            try:
                temp = float(weather['AirTemperature'])
                # 氣象署無資料常回傳 -99.0
                if temp > -50:
                    humid = float(weather['RelativeHumidity'])
                    wind = float(weather['WindSpeed'])
                    rain = float(weather['Now']['Precipitation'])
                    if humid < 0: humid = 75
                    if wind < 0: wind = 0
                    if rain < 0: rain = 0
                    
                    # 以「縣市+鄉鎮」作為 Key，只存最新的有效資料
                    valid_stations_by_town[full_town_key] = {
                        "name": station_name,
                        "data": {"temp": temp, "humidity": humid, "wind_speed": wind, "rain": rain}
                    }
                    count += 1
            except: continue
        print(f"✅ 有效運作中測站: {count} 個")
    except Exception as e:
        print(f"❌ 觀測資料庫建立失敗: {e}")

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

    print("📡 開始一對一嚴格配對...")
    
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
                town_key = f"{city_name}{town_name}"

                # ---------------------------------------------------------
                # 🛑 新邏輯：是就是，不是就不是。絕不猜測。
                # ---------------------------------------------------------
                final_obs_data = None
                source_station_name = "測站故障 / 無測站"
                is_station_broken = True

                # 唯一檢查點：該鄉鎮是否有回傳正常的觀測資料？
                if town_key in valid_stations_by_town:
                    final_obs_data = valid_stations_by_town[town_key]['data']
                    source_station_name = valid_stations_by_town[town_key]['name']
                    is_station_broken = False

                # --- 獲取預報資料 (維持不變，僅用於 7 日預報與天氣圖示) ---
                forecast_wx = "多雲"
                daily_agg = {}

                for el in weather_elements:
                    e_name = el.get('elementName', el.get('ElementName'))
                    time_list = el.get('time', el.get('Time', []))
                    
                    if e_name == 'Wx' and time_list:
                         vals = time_list[0].get('elementValue', time_list[0].get('ElementValue', []))
                         if vals: forecast_wx = vals[0].get('value', '多雲')

                    for t in time_list:
                        start_time = t.get('startTime', t.get('StartTime', ''))
                        vals = t.get('elementValue', t.get('ElementValue', []))
                        if not vals: continue
                        val_str = vals[0].get('value', '0')

                        if len(start_time) >= 10:
                            date_str = start_time[:10] 
                            if date_str not in daily_agg:
                                daily_agg[date_str] = { "temps": [], "pops": [], "wx": [] }
                            
                            if e_name == 'T':
                                try: daily_agg[date_str]["temps"].append(int(val_str))
                                except: pass
                            elif e_name == 'PoP12h':
                                try: daily_agg[date_str]["pops"].append(int(val_str))
                                except: pass
                            elif e_name == 'Wx':
                                daily_agg[date_str]["wx"].append(val_str)

                daily_forecast = []
                sorted_dates = sorted(daily_agg.keys())
                
                for date in sorted_dates:
                    data = daily_agg[date]
                    if data["temps"]:
                        day_display = date[5:].replace('-', '/')
                        wx_condition = max(set(data["wx"]), key=data["wx"].count) if data["wx"] else "多雲"
                        pop_prob = max(data["pops"]) if data["pops"] else 0

                        daily_forecast.append({
                            "day": day_display,
                            "high": max(data["temps"]),
                            "low": min(data["temps"]),
                            "condition": wx_condition,
                            "prob": f"{pop_prob}%"
                        })
                
                # --- 最終判定 ---
                if is_station_broken:
                    # 🔴 測站故障或不存在：顯示無資料
                    final_temp = "--"
                    apparent_temp_str = "--"
                    final_wx = forecast_wx # 圖示仍參考預報
                    final_rain = 0
                    final_ws = 0
                else:
                    # ✅ 正常顯示該鄉鎮資料
                    final_temp = str(int(final_obs_data['temp']))
                    final_rain = final_obs_data['rain']
                    final_ws = final_obs_data['wind_speed']
                    final_wx = "雨天" if final_rain > 0 else forecast_wx 

                indices = calculate_lifestyle_indices(weather_elements, final_obs_data if not is_station_broken else {}, is_broken=is_station_broken)
                my_aqi = aqi_map.get(city_name, 35)

                if not is_station_broken:
                    apparent_temp_str = str(indices['apparent_temp'])

                # 產生精準語錄或故障警示
                pure_advice = get_taiwanese_quote(
                    apparent_temp=indices.get('apparent_temp', 0) if not is_station_broken else 0, 
                    weather=final_wx, 
                    is_raining=(final_rain > 0 or "雨" in final_wx),
                    wind_speed=final_ws,
                    is_broken=is_station_broken
                )

                processed_data = {
                    "city": city_name,
                    "district": town_name,
                    "temp": final_temp, # "--" 或 數字字串
                    "apparent_temp": apparent_temp_str, # "--" 或 數字字串
                    "weather": final_wx,
                    "aqi": my_aqi,
                    "station_source": source_station_name, 
                    "description": pure_advice,
                    "suggestions": indices,
                    "daily_forecast": daily_forecast[:7],
                    "update_time": tw_now_str 
                }

                file_path = f"data/{city_name}{town_name}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(processed_data, f, ensure_ascii=False)
            
            print(f"✅ {city_name} 完成")
            
        except Exception as e:
            print(f"❌ {city_name} 錯誤: {e}")

    print("🎉 資料庫更新完畢！(純 O-A0003-001 絕對精準版)")

if __name__ == "__main__":
    fetch_data()
