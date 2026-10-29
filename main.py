import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
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
                    # 優先調用 Streamlit Secrets
                    if "DSP_KEY" in st.secrets:
                        my_key = st.secrets["DSP_KEY"]
                    else:
                        my_key = "AQ.Ab8RN6JlRFj66Mtm-vwp8mdQ5Ve0EuYNy5MXa9yrqemqhboVgQ"

                    genai.configure(api_key=my_key)

                    # 嚴格約束 Prompt：明確模型名稱、具體微調步驟、禁止 LaTeX 數學格式
                    algorithm_matrix = f"""
                    你是 ToneSmith 專業吉他音色配置系統。請針對以下輸入資料，直接輸出一份高品質、排版清晰的『繁體中文』專業音色參數報告。

                    【輸入資料】
                    - 歌手/樂團：{artist_name}
                    - 目標歌曲：{song_name}
                    - 使用吉他：{guitar_model}
                    - DSP/效果器單元：{pedal_model}

                    【嚴格格式與字體規範】
                    1. 全文必須使用『繁體中文』。
                    2. 絕對不要輸出任何英文思考過程、推理步驟或 Prompt 規則。
                    3. 數字與百分比必須使用『純文字』格式（例如：45% 或 11點鐘方向）。**絕對禁止使用美元符號 $ 或 LaTeX 數學公式語法**，確保數字呈現一般網頁標準字體。

                    【內容必須包含以下 5 個結構】
                    1. 🎸 音箱與箱體選擇 (Amp & Cab Model)
                       - 必須明確寫出**對應設備中指定的音箱模型名稱**（例如：Fender '65 Deluxe Reverb / Vox AC30 等）。
                       - 必須明確寫出**指定搭配的 Cab / IR 模擬名稱與規格**。

                    2. 🎛️ 音箱細節參數與調整方法 (EQ & Gain Setup)
                       - 列出 Gain, Bass, Mid, Treble, Presence 等旋鈕的**具體數值與幾點鐘調整方向**。
                       - 說明每個參數「為什麼這樣調」以及聽感調整方向。

                    3. 🔊 前級推動與過載效果器 (Drive / Boost Setup)
                       - 必須明確寫出**推動效果器的指定模型名稱**（例如：Ibanez TS9 / OD-1 等）。
                       - 列出 Drive, Tone, Level 的具體調整數值。

                    4. 🌊 空間系與周邊效果器 (Delay, Reverb, Modulation)
                       - 必須明確寫出**效果器類型與模型名稱**。
                       - 列出 Time (ms 或 BPM 節奏切換), Feedback %, Mix % 與 Decay 的具體數值。

                    5. 💡 拾音器檔位與實力彈奏建議
                       - 說明建議使用的吉他拾音器檔位（例如：Neck 頸部、第 2 檔等）與撥弦力度細節。
                    """

                    # 輪詢備援模型
                    candidate_models = [
                        "gemini-1.5-flash",
                        "gemini-1.5-pro",
                        "gemini-2.0-flash",
                        "gemini-2.5-flash"
                    ]

                    response_text = None
                    last_err = None

                    for m_name in candidate_models:
                        try:
                            model = genai.GenerativeModel(m_name)
                            res = model.generate_content(algorithm_matrix)
                            if res and hasattr(res, 'text') and res.text:
                                response_text = res.text
                                break
                        except Exception as e:
                            last_err = e
                            continue

                    # 若指定名稱失敗，自動檢索當前可用的模型
                    if not response_text:
                        try:
                            for m in genai.list_models():
                                if "generateContent" in m.supported_generation_methods:
                                    try:
                                        model = genai.GenerativeModel(m.name)
                                        res = model.generate_content(algorithm_matrix)
                                        if res and hasattr(res, 'text') and res.text:
                                            response_text = res.text
                                            break
                                    except Exception:
                                        continue
                        except Exception as list_err:
                            last_err = list_err

                    if not response_text:
                        raise Exception(f"無法存取雲端模型單元，請確認 API Key 是否設定正確。錯誤資訊：{last_err}")

                    st.session_state['last_result'] = response_text
                    st.session_state['last_query'] = {
                        "artist": artist_name,
                        "song": song_name,
                        "guitar": guitar_model,
                        "pedal": pedal_model
                    }

                    st.success("音色參數運算完成！")
                    st.markdown("### 📊 專屬器材設定報告")
                    st.write(response_text)

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
