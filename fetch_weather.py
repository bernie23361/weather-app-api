import requests
import json
import os
import time
from datetime import datetime, timedelta

# --- 🕒 台灣時間小幫手 ---
def get_taiwan_now():
    # GitHub Action 機器人是在標準時間 (UTC)，我們要手動加 8 小時
    return datetime.utcnow() + timedelta(hours=8)

def parse_time_str(t_str):
    # 解析氣象署的時間格式 '2025-01-23T06:00:00+08:00'
    # 我們只取前 19 個字元來轉換，忽略時區字串以避免相容性問題
    return datetime.strptime(t_str[:19], "%Y-%m-%dT%H:%M:%S")

# --- 🧠 核心大腦：9 大生活指數運算邏輯 (含精準對時) ---
def calculate_lifestyle_indices(weather_elements):
    now = get_taiwan_now()

    # 🛠️ 萬用數據提取器：能精準抓到「現在」或「未來」的數據
    def get_values(code, mode='current'):
        vals = []
        for item in weather_elements:
            # 大小寫相容
            e_name = item.get('elementName', item.get('ElementName'))
            
            if e_name == code:
                # 取得時間列表 (大小寫相容)
                time_list = item.get('time', item.get('Time', []))
                
                for t in time_list:
                    # 解析時間段
                    start_str = t.get('startTime', t.get('StartTime'))
                    end_str = t.get('endTime', t.get('EndTime'))
                    
                    if not start_str or not end_str: continue
                    
                    start_dt = parse_time_str(start_str)
                    end_dt = parse_time_str(end_str)

                    # 取值 (大小寫相容)
                    e_vals = t.get('elementValue', t.get('ElementValue', []))
                    if not e_vals: continue
                    val = float(e_vals[0].get('value', e_vals[0].get('Value', '0')))

                    # 🎯 模式 A: 抓取「現在」 (Current)
                    # 邏輯：現在時間落在這個時段內 (Start <= Now < End)
                    if mode == 'current':
                        if start_dt <= now < end_dt:
                            return val # 找到就回傳
                        
                        # 補救措施：如果現在時間已經超過最後一個預報(極少見)，
                        # 或是資料還沒更新，找「離現在最近的未來」
                        if start_dt > now:
                            # 如果還沒找到值，先把這個存起來當備案
                            if not vals: vals.append(val)
                    
                    # 🔮 模式 B: 抓取「未來 24 小時」 (Future)
                    # 邏輯：抓取開始時間在 24 小時內的所有數據
                    elif mode == 'future':
                        if now <= start_dt <= (now + timedelta(hours=24)):
                            vals.append(val)
        
        # 如果沒抓到 (mode='current' 卻沒對中時段)，回傳備案的第一筆
        if mode == 'current':
            return vals[0] if vals else 0
        return vals if vals else [0]

    # --- 1. 抓取精準數據 ---
    # 這些都只抓「現在這一刻」的數值
    curr_t = get_values('T', 'current')     # 氣溫
    curr_at = get_values('AT', 'current')   # 體感溫度 (重要！)
    curr_pop = get_values('PoP12h', 'current') # 降雨機率
    curr_rh = get_values('RH', 'current')   # 濕度
    curr_ws = get_values('WS', 'current')   # 風速
    curr_uvi = get_values('UVI', 'current') # 紫外線

    # --- 2. 抓取趨勢數據 (給洗車、曬衣用) ---
    future_pops = get_values('PoP12h', 'future') # 未來降雨趨勢
    # 如果未來 24 小時任一時段降雨機率 > 40%，就算會下雨
    max_pop_24h = max(future_pops) if isinstance(future_pops, list) else future_pops
    
    # 抓取未來溫差 (給感冒指數用)
    future_temps = get_values('T', 'future')
    if isinstance(future_temps, list) and len(future_temps) > 1:
        temp_diff = max(future_temps) - min(future_temps)
    else:
        temp_diff = 0

    # --- 🧮 開始計算指數 (邏輯優化版) ---

    # 1. 👕 穿衣建議 (改用體感溫度 AT 判斷，比 T 更準)
    if curr_at < 15: clothing = "厚外套"
    elif 15 <= curr_at < 20: clothing = "夾克/風衣"
    elif 20 <= curr_at < 24: clothing = "薄外套"
    elif 24 <= curr_at < 28: clothing = "透氣短袖"
    else: clothing = "清涼透氣"

    # 2. 🚲 騎車指數
    if curr_pop > 20: cycling = "不建議" 
    elif curr_ws > 5: cycling = "需防風" # 風速 > 5m/s 騎車會晃
    elif curr_at > 33: cycling = "太熱了"
    else: cycling = "非常適宜"

    # 3. 🛡️ 防曬指數
    if curr_uvi >= 8: sunscreen = "極強"
    elif curr_uvi >= 6: sunscreen = "高"
    elif curr_uvi >= 3: sunscreen = "中"
    else: sunscreen = "弱"

    # 4. ☀️ 曬衣指數 (看趨勢)
    if max_pop_24h > 30: laundry = "不宜"
    elif curr_rh > 80: laundry = "不易乾"
    else: laundry = "適宜"

    # 5. 🚗 洗車指數 (看趨勢)
    if max_pop_24h > 40: car_wash = "不宜"
    elif curr_pop > 10: car_wash = "不宜"
    else: car_wash = "適宜"

    # 6. ✨ 保養指數
    if curr_rh < 45: skincare = "重保濕"
    elif curr_t > 28 and curr_rh > 75: skincare = "控油清爽"
    else: skincare = "輕保濕"

    # 7. 🩺 感冒指數
    if temp_diff > 9: cold_risk = "易發(溫差大)"
    elif curr_t < 14: cold_risk = "注意保暖"
    else: cold_risk = "低風險"

    # 8. 🐕 寵物散步
    if curr_pop > 30: dog_walk = "不推薦"
    elif curr_t > 31: dog_walk = "防燙腳"
    elif curr_t < 13: dog_walk = "穿衣防寒"
    else: dog_walk = "推薦"

    # 9. 🏃 運動指數
    if curr_pop > 30: sport = "室內佳"
    elif curr_at > 34: sport = "防中暑"
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
    }, curr_t, int(curr_at) # 回傳指數，順便回傳現在氣溫和體感

def fetch_data():
    cwa_key = os.getenv("CWA_API_KEY")
    if not cwa_key:
        print("❌ 錯誤: 找不到 CWA_API_KEY")
        return

    if not os.path.exists("data"):
        os.makedirs("data")

    # 22 縣市 API 代號
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

    print(f"🚀 開始抓取... (校正時間: {get_taiwan_now().strftime('%Y-%m-%d %H:%M:%S')})")
    
    for city_name, api_id in county_api_list.items():
        try:
            url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{api_id}?Authorization={cwa_key}&format=JSON"
            res = requests.get(url)
            data = res.json()
            records = data.get('records', {})
            
            # 結構相容
            locations_raw = []
            if 'locations' in records: locations_raw = records['locations'][0]['location']
            elif 'Locations' in records: locations_raw = records['Locations'][0]['Location']
            elif 'location' in records: locations_raw = records['location']
            
            for loc in locations_raw:
                town_name = loc.get('locationName', loc.get('LocationName', '未知'))
                weather_elements = loc.get('weatherElement', loc.get('WeatherElement', []))
                
                # --- 計算指數 (接收回傳的建議、溫度、體感) ---
                indices, real_temp, real_at = calculate_lifestyle_indices(weather_elements)
                
                # 取得天氣現象 (也加入對時功能)
                current_wx = "多雲"
                for el in weather_elements:
                     # 簡單遍歷，找到包含現在時間的 Wx
                     e_name = el.get('elementName', el.get('ElementName'))
                     if e_name == 'Wx':
                         time_list = el.get('time', el.get('Time', []))
                         for t in time_list:
                             start = parse_time_str(t.get('startTime', t.get('StartTime')))
                             end = parse_time_str(t.get('endTime', t.get('EndTime')))
                             if start <= get_taiwan_now() < end:
                                 e_vals = t.get('elementValue', t.get('ElementValue', []))
                                 if e_vals:
                                     current_wx = e_vals[0].get('value', e_vals[0].get('Value', ''))
                                 break

                processed_data = {
                    "city": city_name,
                    "district": town_name,
                    "temp": str(int(real_temp)), # 修正為 int 去掉小數點
                    "apparent_temp": str(int(real_at)), # 新增體感溫度
                    "weather": current_wx,
                    "suggestions": indices,
                    "update_time": get_taiwan_now().strftime("%Y-%m-%d %H:%M:%S")
                }

                file_path = f"data/{town_name}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(processed_data, f, ensure_ascii=False)
            
            print(f"✅ {city_name} 完成")
            
        except Exception as e:
            print(f"❌ {city_name} 錯誤: {e}")

    print("🎉 資料更新完畢！")

if __name__ == "__main__":
    fetch_data()
