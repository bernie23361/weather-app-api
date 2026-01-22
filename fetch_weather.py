import requests
import json
import os
import time

# --- 🧠 核心大腦：9 大生活指數運算邏輯 ---
def calculate_lifestyle_indices(weather_elements):
    # 1. 提取未來 24 小時的關鍵數據 (做趨勢判斷用)
    # 我們需要把未來幾筆預報資料抓出來做統計
    temps = []   # 溫度
    pops = []    # 降雨機率
    rhs = []     # 濕度
    wds = []     # 風速
    uvis = []    # 紫外線
    ats = []     # 體感溫度

    # 提取數據 helper (CWA 的結構是一序列的時間段)
    def get_values(code):
        vals = []
        for item in weather_elements:
            if item['elementName'] == code:
                # 抓取前 4 筆資料 (約未來 12~24 小時)
                for t in item['time'][:4]: 
                    val = t['elementValue'][0]['value']
                    try:
                        vals.append(float(val))
                    except:
                        vals.append(0)
        return vals

    temps = get_values('T')
    pops = get_values('PoP12h') # 12小時降雨機率
    rhs = get_values('RH')
    wds = get_values('WS')
    uvis = get_values('UVI')
    ats = get_values('AT')

    # 取得「當下」數值 (第 0 筆)
    curr_t = temps[0] if temps else 25
    curr_pop = pops[0] if pops else 0
    curr_rh = rhs[0] if rhs else 75
    curr_ws = wds[0] if wds else 2
    curr_uvi = uvis[0] if uvis else 0
    curr_at = ats[0] if ats else curr_t

    # 未來 24h 最大降雨機率 (決定洗車/曬衣)
    max_pop_24h = max(pops) if pops else curr_pop
    # 日夜溫差 (決定感冒)
    temp_diff = (max(temps) - min(temps)) if temps else 0

    # --- 🧮 開始計算指數 ---

    # 1. 👕 穿衣建議 (使用體感溫度 AT)
    if curr_at < 15: clothing = "厚外套"
    elif 15 <= curr_at < 20: clothing = "夾克/風衣"
    elif 20 <= curr_at < 24: clothing = "薄外套"
    elif 24 <= curr_at < 28: clothing = "透氣短袖"
    else: clothing = "清涼透氣"

    # 2. 🚲 騎車指數 (風速 + 降雨)
    if curr_pop > 20: cycling = "不建議" # 下雨危險
    elif curr_ws > 4: cycling = "需防風" # 風大
    elif curr_at > 32: cycling = "太熱了"
    else: cycling = "非常適宜"

    # 3. 🛡️ 防曬指數 (UVI)
    if curr_uvi >= 8: sunscreen = "極強"
    elif curr_uvi >= 6: sunscreen = "高"
    elif curr_uvi >= 3: sunscreen = "中"
    else: sunscreen = "弱"

    # 4. ☀️ 曬衣指數 (看未來 24h 降雨 + 目前濕度)
    if max_pop_24h > 30: laundry = "不宜" # 之後會下雨
    elif curr_rh > 85: laundry = "不易乾" # 太濕
    else: laundry = "適宜"

    # 5. 🚗 洗車指數 (看未來 24h 降雨)
    if max_pop_24h > 40: car_wash = "不宜" # 明天會下雨別洗
    elif curr_pop > 10: car_wash = "不宜"
    else: car_wash = "適宜"

    # 6. ✨ 保養指數 (濕度 + 溫度)
    if curr_rh < 50: skincare = "重保濕" # 太乾
    elif curr_t > 28 and curr_rh > 80: skincare = "控油清爽"
    else: skincare = "輕保濕"

    # 7. 🩺 感冒指數 (溫差 + 低溫)
    if temp_diff > 10: cold_risk = "易發(溫差大)"
    elif curr_t < 14: cold_risk = "注意保暖"
    else: cold_risk = "低風險"

    # 8. 🐕 寵物散步 (氣溫 + 降雨)
    if curr_pop > 30: dog_walk = "不推薦"
    elif curr_t > 30: dog_walk = "防燙腳" # 地面太燙
    elif curr_t < 12: dog_walk = "穿衣防寒"
    else: dog_walk = "推薦"

    # 9. 🏃 運動指數 (降雨 + 空氣 - 這裡暫缺 AQI，先用天氣判斷)
    if curr_pop > 30: sport = "室內佳"
    elif curr_t > 33: sport = "防中暑"
    else: sport = "戶外佳"

    return {
        "clothing": clothing,
        "cycling": cycling,
        "sunscreen": sunscreen,
        "laundry": laundry,
        "car_wash": car_wash,
        "skincare": skincare,
        "cold_risk": cold_risk,
        "dog_walk": dog_walk,
        "sport": sport
    }

def fetch_data():
    cwa_key = os.getenv("CWA_API_KEY")
    if not cwa_key:
        print("❌ 錯誤: 找不到 CWA_API_KEY")
        return

    if not os.path.exists("data"):
        os.makedirs("data")

    # 22 縣市 API 代號 (F-D0047-0XX 綜合預報)
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

    print("🚀 開始運算高精度生活指數...")
    
    for city_name, api_id in county_api_list.items():
        try:
            # 抓取未來 2 天預報
            url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{api_id}?Authorization={cwa_key}&format=JSON"
            res = requests.get(url)
            data = res.json()
            records = data.get('records', {})
            
            # 結構相容處理
            locations_raw = []
            if 'locations' in records: locations_raw = records['locations'][0]['location']
            elif 'Locations' in records: locations_raw = records['Locations'][0]['Location']
            elif 'location' in records: locations_raw = records['location']
            
            for loc in locations_raw:
                town_name = loc.get('locationName', loc.get('LocationName', '未知'))
                weather_elements = loc.get('weatherElement', loc.get('WeatherElement', []))
                
                # --- 核心：計算 9 大指數 ---
                indices = calculate_lifestyle_indices(weather_elements)

                # --- 取得基本天氣資訊 ---
                # 這裡簡單抓第一筆做顯示
                current_temp = "25"
                current_wx = "多雲"
                for el in weather_elements:
                    code = el.get('elementName')
                    val = el.get('time')[0]['elementValue'][0]['value']
                    if code == 'T': current_temp = val
                    if code == 'Wx': current_wx = val

                processed_data = {
                    "city": city_name,
                    "district": town_name,
                    "temp": current_temp,
                    "weather": current_wx,
                    "suggestions": indices, # 這裡面現在有超準的 9 大指數了
                    "update_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }

                file_path = f"data/{town_name}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(processed_data, f, ensure_ascii=False)
            
            print(f"✅ {city_name} 計算完成")
            
        except Exception as e:
            print(f"❌ {city_name} 錯誤: {e}")

    print("🎉 全台指數運算完畢！")

if __name__ == "__main__":
    fetch_data()
