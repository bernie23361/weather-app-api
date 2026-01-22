import requests
import json
import os
import time

# --- 🧠 核心大腦：9 大生活指數運算邏輯 (修復大小寫問題) ---
def calculate_lifestyle_indices(weather_elements):
    
    # 提取數據 helper (加入大小寫防呆機制)
    def get_values(code):
        vals = []
        for item in weather_elements:
            # 兼容 elementName 和 ElementName
            e_name = item.get('elementName', item.get('ElementName'))
            
            if e_name == code:
                # 兼容 time 和 Time
                time_list = item.get('time', item.get('Time', []))
                
                # 抓取前 4 筆資料 (約未來 12~24 小時)
                for t in time_list[:4]: 
                    # 兼容 elementValue 和 ElementValue
                    e_vals = t.get('elementValue', t.get('ElementValue', []))
                    if e_vals:
                        # 兼容 value 和 Value
                        val = e_vals[0].get('value', e_vals[0].get('Value', '0'))
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
    if temp_diff > 10: cold
