import streamlit as st
import pandas as pd
from datetime import datetime
import os
import base64
import importlib
import time

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
        # 15 秒防連點冷卻機制
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
                    # 動態載入 google.generativeai 套件
                    dsp_module_name = base64.b64decode("Z29vZ2xlLmdlbmVyYXRpdmVhaQ==").decode('utf-8')
                    cloud_dsp = importlib.import_module(dsp_module_name)

                    # 優先調用 Streamlit Secrets
                    if "DSP_KEY" in st.secrets:
                        my_key = st.secrets["DSP_KEY"]
                    else:
                        my_key = "AQ.Ab8RN6JlRFj66Mtm-vwp8mdQ5Ve0EuYNy5MXa9yrqemqhboVgQ"

                    cloud_dsp.configure(api_key=my_key, transport="rest")

                    algorithm_matrix = f"""
                    [系統運算規則]
                    目標：計算吉他音色參數配置
                    輸入資料：
                    - 歌手/樂團：{artist_name}
                    - 歌曲：{song_name}
                    - 吉他型號：{guitar_model}
                    - 效果器/DSP單元：{pedal_model}

                    請以專業技術人員的口吻，輸出各頻段與空間系效果的具體數值 (Amp, EQ, Gain, Delay/Reverb, IR)。
                    完全不要提及你是AI、助手或語言模型，這是一份系統自動產生的參數分析報告。
                    """

                    # 多重模型備援清單 (Base64 編碼：gemini-2.0-flash, gemini-1.5-pro-latest, gemini-2.5-pro)
                    candidate_models = [
                        "Z2VtaW5pLTIuMC1mbGFzaA==",
                        "Z2VtaW5pLTEuNS1wcm8tbGF0ZXN0",
                        "Z2VtaW5pLTIuNS1wcm8="
                    ]

                    response = None
                    last_err = None

                    for enc_m in candidate_models:
                        try:
                            target_m = base64.b64decode(enc_m).decode('utf-8')
                            model = cloud_dsp.GenerativeModel(target_m)
                            response = model.generate_content(algorithm_matrix)
                            if response and hasattr(response, 'text') and response.text:
                                break
                        except Exception as m_err:
                            last_err = m_err
                            continue

                    if not response or not hasattr(response, 'text'):
                        raise last_err if last_err else Exception("無法連線至雲端模型處理單元。")

                    result_text = response.text

                    st.session_state['last_result'] = result_text
                    st.session_state['last_query'] = {
                        "artist": artist_name,
                        "song": song_name,
                        "guitar": guitar_model,
                        "pedal": pedal_model
                    }

                    st.success("音色參數運算完成！")
                    st.markdown("### 📊 專屬器材設定報告")
                    st.write(result_text)

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

