import streamlit as st
import pandas as pd
from datetime import datetime
import time
import re
import requests
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection

# 介面設定
st.set_page_config(page_title="ToneSmith 專業吉他音色配置系統", page_icon="🎸")
st.title("🎸 ToneSmith 智慧數位訊號參數配置系統")
st.write("透過雲端數位訊號處理 (DSP) 演算法，為您的設備計算最佳音箱與效果器參數。")
st.markdown("---")

# 初始化 Google Sheets 讀取連線
conn = st.connection("gsheets", type=GSheetsConnection)

# 快取優化：讀取歷史資料庫
@st.cache_data(ttl=600)
def fetch_gsheet_data():
    try:
        return conn.read(ttl=600)
    except Exception:
        return pd.DataFrame()

def get_historical_feedback(artist, song, pedal):
    try:
        df = fetch_gsheet_data()
        if df.empty:
            return "目前尚無歷史實測紀錄。"

        matched = df[
            (df['artist'].astype(str).str.contains(artist, case=False, na=False)) |
            (df['song'].astype(str).str.contains(song, case=False, na=False)) |
            (df['pedal'].astype(str).str.contains(pedal, case=False, na=False))
        ]

        feedback_notes = []
        for _, row in matched.iterrows():
            comment_text = str(row.get('comments', '')).strip()
            rating_val = str(row.get('rating', ''))
            if comment_text and comment_text.lower() != 'nan':
                feedback_notes.append(f"- 【歷史實測評分 {rating_val}星】：{comment_text}")

        if feedback_notes:
            return "\n".join(feedback_notes[-3:])
        return "目前尚無此歌曲/設備的特定修正紀錄。"
    except Exception:
        return "無法取得歷史紀錄，請按標準演算法計算。"

# 穩定版文字清理器：解決斷流、灰底框與標題星號
def sanitize_report(raw_text):
    if not raw_text:
        return raw_text
    
    # 1. 徹底移除 ``` 及 LaTeX 美元符號
    cleaned = raw_text.replace("$", "")
    cleaned = re.sub(r'```[a-zA-Z]*', '', cleaned)
    cleaned = cleaned.replace("```", "")
    
    # 2. 找到開頭大標題，切除前面無關的導引文字
    match = re.search(r'(#+\s*🎸|#+\s*ToneSmith)', cleaned)
    if match:
        cleaned = cleaned[match.start():]
        
    lines = cleaned.split("\n")
    valid_lines = []
    
    for line in lines:
        s = line.strip()
        
        # 濾除 AI 自我解說行
        if any(s.startswith(k) for k in [
            "*Self-Correction", "User Input:", "Final Polish", "Note:", "Notice:"
        ]):
            continue
            
        # 清除標題行開頭被誤加的星號清單點點 (* ## -> ##)
        s = re.sub(r'^\*\s*(#+)', r'\1', s)
        
        valid_lines.append(s)
        
    return "\n".join(valid_lines).strip()

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
        COOLDOWN_SECONDS = 10
        now = time.time()
        last_call = st.session_state.get('last_api_call_time', 0)
        time_passed = now - last_call

        if time_passed < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - time_passed)
            st.warning(f"⚠️ 雲端 DSP 核心冷卻中，請等待 {remaining} 秒後再試。")
        else:
            st.session_state['last_api_call_time'] = now

            with st.spinner("正在連線至雲端 DSP 核心進行運算中..."):
                try:
                    if "DSP_KEY" in st.secrets:
                        my_key = st.secrets["DSP_KEY"]
                    else:
                        my_key = "AQ.Ab8RN6JlRFj66Mtm-vwp8mdQ5Ve0EuYNy5MXa9yrqemqhboVgQ"

                    genai.configure(api_key=my_key)

                    history_feedback = get_historical_feedback(artist_name, song_name, pedal_model)

                    system_prompt = f"""
你是 ToneSmith 專業吉他音色配置系統。請直接完整輸出一份含 5 個章節的繁體中文音色報告。

【歷史樂手實測修正紀錄】
{history_feedback}

【必須完整輸出的 Markdown 範本結構 (請務必將 1 到 5 章節全部寫完，不可中斷)】

# 🎸 ToneSmith 音色配置報告：[歌手/樂團] - 《[歌曲]》

> 📌 **設備配置**：[吉他型號] ➔ [DSP/效果器型號]

---

## 1. 🔊 音箱與箱體選擇 (Amp & Cab Model)
* **音箱模型**：`[模型名稱]`
* **箱體/IR**：`[箱體名稱]`

## 2. 🎛️ 音箱細節參數與調整方法 (EQ & Gain Setup)
* **Gain**：`35%` (10點鐘方向) — *聽感說明*
* **Bass**：`45%` (11點鐘方向) — *聽感說明*
* **Mid**：`55%` (1點鐘方向) — *聽感說明*
* **Treble**：`65%` (2點鐘方向) — *聽感說明*
* **Presence**：`60%` (1點鐘方向) — *聽感說明*

## 3. ⚡ 前級推動與過載效果器 (Drive / Boost Setup)
* **效果器模型**：`[模型名稱]`
* **參數設定**：Drive `15%`, Tone `55%`, Level `65%`

## 4. 🌊 空間系與周邊效果器 (Delay, Reverb, Mod)
* **Delay**：`Digital Delay` (Time `380ms`, Feedback `20%`, Mix `15%`)
* **Reverb**：`Hall Reverb` (Decay `2.2s`, Mix `20%`)

## 5. 💡 拾音器檔位與實力彈奏建議
* **建議檔位**：`第 4 檔` (主歌), `第 2 檔` (副歌)
* **彈奏細節**：動態與撥弦力度說明。

【絕對規範】
1. 開頭必須直接從「# 🎸 ToneSmith」開始。
2. 必須完整產生全部 5 個章節，絕對不能中途停止。
3. 嚴禁加入範本以外的自訂欄位（例如「選擇理由」）。
4. 嚴禁使用程式碼區塊 (```) 包裹全文。
"""

                    user_prompt = f"""
請計算以下器材設定：
- 歌手/樂團：{artist_name}
- 目標歌曲：{song_name}
- 使用吉他：{guitar_model}
- DSP/效果器單元：{pedal_model}
"""

                    gen_config = genai.types.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=2500
                    )

                    target_models = []
                    try:
                        for m in genai.list_models():
                            if 'generateContent' in m.supported_generation_methods:
                                target_models.append(m.name)
                        flash_first = [m for m in target_models if 'flash' in m.lower()]
                        others = [m for m in target_models if m not in flash_first]
                        target_models = flash_first + others
                    except Exception:
                        target_models = ["gemini-2.0-flash", "gemini-1.5-flash"]

                    raw_response = None
                    last_err = None

                    for m_name in target_models:
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
                        raise Exception(f"無法存取雲端模型單元，請確認 API Key。錯誤資訊：{last_err}")

                    final_report = sanitize_report(raw_response)

                    st.session_state['last_result'] = final_report
                    st.session_state['last_query'] = {
                        "artist": artist_name,
                        "song": song_name,
                        "guitar": guitar_model,
                        "pedal": pedal_model
                    }

                    st.success("音色參數運算完成！")
                    st.markdown(final_report)

                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "Quota exceeded" in err_str or "ResourceExhausted" in err_str:
                        st.error("⚠️ 雲端運算連線較繁忙，請等待 10 秒後再試。")
                    else:
                        st.error(f"系統偵錯資訊：{e}")

# 回饋提交區塊
if 'last_result' in st.session_state:
    st.markdown("---")
    st.markdown("### ✍️ 現場實測回饋與微調")
    st.write("請依照實際彈奏聽感給予評分與建議，數據將同步存入雲端資料庫供 AI 後續運算學習。")

    rating = st.slider("音色還原度評分 (1星 = 差異極大，5星 = 完美還原)", 1, 5, 4)
    comments = st.text_area("具體微調建議 (例如：高頻太刺、破音Gain開太高、空間系殘響需要再少一點等)")

    if st.button("提交回饋並儲存數據"):
        try:
            with st.spinner("正在將數據寫入雲端資料庫..."):
                payload = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "artist": st.session_state['last_query']['artist'],
                    "song": st.session_state['last_query']['song'],
                    "guitar": st.session_state['last_query']['guitar'],
                    "pedal": st.session_state['last_query']['pedal'],
                    "generated_result": st.session_state['last_result'],
                    "rating": rating,
                    "comments": comments
                }

                webapp_url = st.secrets.get("GSHEET_WEBAPP_URL", "")
                if not webapp_url:
                    st.error("未設定 GSHEET_WEBAPP_URL，請至 Streamlit Secrets 配置。")
                else:
                    response = requests.post(webapp_url, json=payload, timeout=10)
                    if response.status_code == 200:
                        st.cache_data.clear()
                        st.success("🎉 回饋數據已成功寫入 Google 試算表！AI 已吸收此實測意見。")
                    else:
                        st.error(f"寫入失敗，狀態碼：{response.status_code}")
        except Exception as write_err:
            st.error(f"寫入資料庫失敗：{write_err}")
