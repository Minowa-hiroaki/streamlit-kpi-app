import streamlit as st
from openai import OpenAI
import sqlite3
import json
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# --- 1. 環境設定とCSSによるレイアウト最適化 ---
load_dotenv()
st.set_page_config(page_title="今日の一歩", layout="wide")

# CSSで極限まで余白を削り、上詰めにする
st.markdown("""
    <style>
    /* メインエリアの上部余白を削除 */
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    /* サイドバーの上部余白を削除 */
    [data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
    /* エキスパンダーや情報の枠の余白を調整 */
    .stAlert { padding: 0.5rem; margin-bottom: 0.5rem; }
    div[data-testid="stExpander"] { margin-top: -1rem; }
    /* ヘッダーの余白調整 */
    h1, h2, h3 { margin-top: 0rem; padding-top: 0rem; }
    </style>
""", unsafe_allow_html=True)

# APIキー設定
api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# --- 2. ユーティリティ関数 ---
def get_file_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def load_json_data(filename):
    path = get_file_path(filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig") as f: return json.load(f)
    return {}

kpi_data = load_json_data("kpi_definitions.json")
employee_master = load_json_data("employee_master.json")

def init_db():
    conn = sqlite3.connect(get_file_path('kpi_app.db'))
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT, role TEXT, content TEXT, turn_count INTEGER, timestamp TEXT)')
    conn.commit()
    conn.close()
init_db()

# --- 3. ログイン管理 ---
if "login_id" not in st.session_state:
    # ログイン画面もコンパクトに
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        st.title("🌱 今日の一歩")
        input_id = st.text_input("社員IDを入力", key="login_input")
        if input_id in employee_master:
            st.session_state.login_id = input_id
            st.rerun()
    st.stop()

user_info = employee_master[st.session_state.login_id]
user_name, dept_name = user_info["name"], user_info["department"]

# --- 4. サイドバー（上詰め表示） ---
with st.sidebar:
    st.markdown("### 🌱 メニュー")
    menu_options = ["振り返り対話", "マイページ（目標・AI相談）"]
    if st.session_state.login_id == "ADMIN01": menu_options.append("管理者画面")
    page = st.radio("表示画面", menu_options, label_visibility="collapsed")
    
    st.divider()

    if page == "振り返り対話":
        st.markdown("### 📈 想定される流れ")
        turns = [("① 共有", "報告"), ("② 深掘りI", "具体化"), ("③ 深掘りII", "リスク"), ("④ 評価", "助言"), ("⑤ 目標", "確定")]
        curr = st.session_state.get("turn_count", 1)
        for i, (t, d) in enumerate(turns, 1):
            color = "#007bff" if i == curr else "#adb5bd"
            st.markdown(f"<p style='color:{color}; margin-bottom:0px;'>{'👉' if i==curr else '　'} {t}</p>", unsafe_allow_html=True)

        st.divider()
        st.markdown(f"**{dept_name}のKPI**")
        for k in kpi_data.get(dept_name, []): st.markdown(f"<small>・{k}</small>", unsafe_allow_html=True)

    if st.button("ログアウト", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. メイン画面エリア ---

if page == "振り返り対話":
    # タイトルとユーザー情報を1行にまとめて上詰め
    col_a, col_b = st.columns([2, 1])
    with col_a: st.subheader(f"💬 {user_name} さんの振り返り")
    with col_b: st.write(f"({dept_name})")

    # --- 前回の目標抽出（AI要約ロジック強化） ---
    conn = sqlite3.connect(get_file_path('kpi_app.db'))
    goal_df = pd.read_sql_query(
        "SELECT content FROM messages WHERE employee_id=? AND role='assistant' AND content LIKE '%完了しました%' ORDER BY timestamp DESC LIMIT 1", 
        conn, params=(st.session_state.login_id,)
    )
    conn.close()
    
    if not goal_df.empty:
        raw_text = goal_df.iloc[0]['content']
        # 目標部分のみを抽出するAIプロンプト（瞬時に要約）
        try:
            summary_res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "以下の文章から『次回の具体的な目標』となる1文だけを抜き出してください。余計な挨拶は不要です。"},
                          {"role": "user", "content": raw_text}]
            )
            goal_text = summary_res.choices[0].message.content
        except:
            goal_text = "目標の取得に失敗しました。"
        
        st.info(f"🎯 **前回の目標：{goal_text}**")
    
    # ガイドメッセージをコンパクトに改行
    st.caption("💡 週一回の共有推奨。アピール・課題・トラブルなど、いつでも共有OKです。")

    # チャット履歴
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "お疲れ様です！今週の出来事（売上、コスト、効率化、トラブル等）を教えてください。"}]
        st.session_state.turn_count = 1

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.write(msg["content"])

    if prompt := st.chat_input("メッセージを入力..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)

        with st.chat_message("assistant"):
            turn = st.session_state.turn_count
            dept_kpis = "、".join(kpi_data.get(dept_name, []))
            system_p = f"あなたは{dept_name}のコーチです。KPI「{dept_kpis}」に基づき対話してください。現在はターン {turn}/5 です。最後は必ず具体的な『次回の目標』を提示し、『今週の振り返りを完了しました』と締めてください。"
            
            res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"system", "content":system_p}] + st.session_state.messages)
            ai_msg = res.choices[0].message.content
            st.write(ai_msg)
            st.session_state.messages.append({"role": "assistant", "content": ai_msg})

            # DB保存とカウントアップ
            conn = sqlite3.connect(get_file_path('kpi_app.db'))
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("INSERT INTO messages (employee_id, role, content, turn_count, timestamp) VALUES (?, ?, ?, ?, ?)", (st.session_state.login_id, "user", prompt, turn, now))
            conn.execute("INSERT INTO messages (employee_id, role, content, turn_count, timestamp) VALUES (?, ?, ?, ?, ?)", (st.session_state.login_id, "assistant", ai_msg, turn, now))
            conn.commit(); conn.close()
            if st.session_state.turn_count < 5:
                st.session_state.turn_count += 1
                st.rerun()

elif page == "マイページ（目標・AI相談）":
    st.subheader("📱 マイページ")
    # ... (マイページ用コードも同様に上詰めCSSが適用されます)