import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
import re
import google.generativeai as genai

# 介面設定
st.set_page_config(page_title="ToneSmith 專業吉他音色配置系統", page_icon="🎸")
st.title("🎸 ToneSmith 智慧數位訊號參數配置系統")
st.write("透過雲端數位訊號處理 (DSP) 演算法，為您的設備計算最佳音箱與效果器參數。")
st.markdown("---")

LOG_FILE = "feedback_log.csv"
def init_log():
    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(columns=["timestamp", "artist", "song", "guitar", "pedal", "generated_result", "rating", "comments"])
        df.to_csv(LOG_FILE, index=False)
init_log()

# 硬性後端文字清理器：無論模型吐出多少英文思考過程，強制全數砍掉
def sanitize_report(raw_text):
    if not raw_text:
        return raw_text
    
    # 清理可能產生的 LaTeX 數學符號包裹 ($)
    cleaned = raw_text.replace("$", "")
    
    # 尋找真正的繁體中文報告開頭關鍵字
    target_markers = ["ToneSmith", "🎸", "音色配置報告", "【專屬器材設定報告】", "1. 🎸", "一、"]
    
    first_index = -1
    for marker in target_markers:
        pos = cleaned.find(marker)
        if pos != -1:
            if first_index == -1 or pos < first_index:
                first_index = pos
                
    # 若找到報告開頭，直接將前面的所有英文思考與前導贅字全數切除
    if first_index != -1:
        cleaned = cleaned[first_index:]
        
    return cleaned.strip()

col1, col2 = st.columns(2)
with col1:
    artist_name = st.text_input("演出歌手或樂團 (例如：美秀集團)")
    guitar_model = st.text_input("使用吉他型號 (例如：Fender Stratocaster)")
with col2:
    song_name = st.text_input("目標曲目名稱 (例如：捲菸)")
    pedal_model = st.text_input("使用 DSP/效果器型號 (例如：NUX MG-30)")

if st.button("開始計算音色參數"):
    if not song_name or not artist_name or not guitar_model or not pedal_model:
        st.warning("請將曲目資訊與硬體設備欄位填寫完整。")
    else:
        COOLDOWN_SECONDS = 15
        now = time.time()
        last_call = st.session_state.get('last_api_call_time', 0)
        time_passed = now - last_call

        if time_passed < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - time_passed)
            st.warning(f"⚠️ 雲端 DSP 核心冷卻中，請等待 {remaining} 秒後再試。")
        else:
            st.session_state['last_api_call_time'] = now

            with st.spinner("正在連線至雲端 DSP 核心進行頻段運算中，請稍候..."):
                try:
                    if "DSP_KEY" in st.secrets:
                        my_key = st.secrets["DSP_KEY"]
                    else:
                        my_key = "AQ.Ab8RN6JlRFj66Mtm-vwp8mdQ5Ve0EuYNy5MXa9yrqemqhboVgQ"

                    genai.configure(api_key=my_key)

                    # 獨立系統指令
                    system_prompt = """
你是 ToneSmith 專業吉他音色配置系統。請直接輸出純繁體中文報告。

【輸出標準格式】
ToneSmith 專業吉他音色配置報告 - [歌手/樂團] 「[歌曲]」

1. 🎸 音箱與箱體選擇 (Amp & Cab Model)
- 音箱模型：必須寫出 DSP/效果器中的特定指定名稱 (例如：Brit Chime)
- 箱體/IR：必須寫出對應搭配的 Cab 模型 (例如：Brit 2x12)

2. 🎛️ 音箱細節參數與調整方法 (EQ & Gain Setup)
- Gain: 35% (11點鐘方向)
- Bass: 45% (11點鐘方向)
- Mid: 55% (1點鐘方向)
- Treble: 65% (2點鐘方向)
- Presence: 60% (1點鐘方向)

3. 🔊 前級推動與過載效果器 (Drive / Boost Setup)
- 效果器模型：指定模型名稱 (例如：T Screamer)
- 參數設定：Drive 15%, Tone 55%, Level 70%

4. 🌊 空間系與周邊效果器 (Delay, Reverb, Modulation)
- Delay：Digital Delay (Time 350ms, Feedback 25%, Mix 15%)
- Reverb：Hall Reverb (Decay 2.0s, Mix 25%)

5. 💡 拾音器檔位與實力彈奏建議
- 檔位選擇與彈奏力度建議。

【嚴格禁令】
- 數字禁止使用 LaTeX 或 $ 符號包裹。
- 全文禁止出現任何英文推理分析、思考過程或 Self-Correction 紀錄。
"""

                    user_prompt = f"""
請計算以下器材設定：
- 歌手/樂團：{artist_name}
- 目標歌曲：{song_name}
- 使用吉他：{guitar_model}
- DSP/效果器單元：{pedal_model}
"""

                    # 低溫設定減少模型的碎碎念
                    gen_config = genai.types.GenerationConfig(temperature=0.2)

                    candidate_models = [
                        "gemini-1.5-flash",
                        "gemini-1.5-pro",
                        "gemini-2.0-flash",
                        "gemini-2.5-flash"
                    ]

                    raw_response = None
                    last_err = None

                    for m_name in candidate_models:
                        try:
                            model = genai.GenerativeModel(
                                m_name,
                                system_instruction=system_prompt,
                                generation_config=gen_config
                            )
                            res = model.generate_content(user_prompt)
                            if res and hasattr(res, 'text') and res.text:
                                raw_response = res.text
                                break
                        except Exception as e:
                            last_err = e
                            continue

                    if not raw_response:
                        try:
                            for m in genai.list_models():
                                if "generateContent" in m.supported_generation_methods:
                                    try:
                                        model = genai.GenerativeModel(
                                            m.name,
                                            system_instruction=system_prompt,
                                            generation_config=gen_config
                                        )
                                        res = model.generate_content(user_prompt)
                                        if res and hasattr(res, 'text') and res.text:
                                            raw_response = res.text
                                            break
                                    except Exception:
                                        continue
                        except Exception as list_err:
                            last_err = list_err

                    if not raw_response:
                        raise Exception(f"無法存取雲端模型單元，請確認 API Key 是否設定正確。錯誤資訊：{last_err}")

                    # 後台程式碼強制打回、切除英文與思考紀錄
                    final_report = sanitize_report(raw_response)

                    st.session_state['last_result'] = final_report
                    st.session_state['last_query'] = {
                        "artist": artist_name,
                        "song": song_name,
                        "guitar": guitar_model,
                        "pedal": pedal_model
                    }

                    st.success("音色參數運算完成！")
                    st.markdown("### 📊 專屬器材設定報告")
                    st.write(final_report)

                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "Quota exceeded" in err_str or "ResourceExhausted" in err_str:
                        st.error("⚠️ 雲端運算連線較繁忙，請等待 15 秒後再點擊一次。")
                    else:
                        st.error(f"系統偵錯資訊：{e}")

if 'last_result' in st.session_state:
    st.markdown("---")
    st.markdown("### ✍️ 現場實測回饋與微調")
    st.write("請依照實際彈奏聽感給予評分與建議，系統將記錄此數據作為後續運算優化依據。")

    rating = st.slider("音色還原度評分 (1星 = 差異極大，5星 = 完美還原)", 1, 5, 4)
    comments = st.text_area("具體微調建議 (例如：高頻太刺、破音Gain開太高、空間系殘響需要再少一點等)")

    if st.button("提交回饋並儲存數據"):
        new_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "artist": st.session_state['last_query']['artist'],
            "song": st.session_state['last_query']['song'],
            "guitar": st.session_state['last_query']['guitar'],
            "pedal": st.session_state['last_query']['pedal'],
            "generated_result": st.session_state['last_result'],
            "rating": rating,
            "comments": comments
        }

        df_log = pd.read_csv(LOG_FILE)
        df_log = pd.concat([df_log, pd.DataFrame([new_data])], ignore_index=True)
        df_log.to_csv(LOG_FILE, index=False)
        st.success("回饋數據已成功儲存！系統已將此微調意見納入後續演算法學習中。")
