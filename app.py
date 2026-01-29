import streamlit as st
from openai import OpenAI
import sqlite3
import json
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# --- 1. 環境設定 ---
load_dotenv()
st.set_page_config(page_title="今日の一歩", layout="wide")

api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("APIキーが見つかりません。")
    st.stop()
client = OpenAI(api_key=api_key)

# --- 2. ユーティリティ ---
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
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT, role TEXT, content TEXT, turn_count INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()
init_db()

# --- 3. ログイン処理 ---
if "login_id" not in st.session_state:
    st.title("🌱 今日の一歩：ログイン")
    input_id = st.text_input("社員IDを入力してください", key="login_input")
    if input_id:
        if input_id in employee_master:
            st.session_state.login_id = input_id
            st.rerun()
        else:
            st.error("IDが正しくありません")
    st.stop()

user_info = employee_master[st.session_state.login_id]
dept_name = user_info["department"]

# --- 4. サイドバーメニュー（ここが肝心です） ---
with st.sidebar:
    st.title("🌱 メニュー")
    menu_options = ["振り返り対話", "マイページ（目標・AI相談）"]
    if st.session_state.login_id == "ADMIN01":
        menu_options.append("管理者画面")
    
    page = st.radio("表示する画面を選択", menu_options)
    st.divider()
    
    if page == "振り返り対話":
        st.markdown("### 💡 今週のKPI")
        for k in kpi_data.get(dept_name, []): st.markdown(f"・{k}")

    if st.button("ログアウト", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. 画面切り替えロジック ---

if page == "振り返り対話":
    st.header(f"💬 {user_info['name']} さんの振り返り")
    # 以前の目標表示
    conn = sqlite3.connect(get_file_path('kpi_app.db'))
    goal_df = pd.read_sql_query("SELECT content FROM messages WHERE employee_id=? AND role='assistant' AND content LIKE '%完了しました%' ORDER BY timestamp DESC LIMIT 1", conn, params=(st.session_state.login_id,))
    conn.close()
    if not goal_df.empty:
        st.info(f"**前回の目標:** {goal_df.iloc[0]['content']}")

    # 対話機能（簡略版）
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "今週はどうでしたか？"}]
        st.session_state.turn_count = 1

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.write(msg["content"])

    if prompt := st.chat_input("入力..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        # AIレスポンスとDB保存の処理（中略）
        st.rerun()

elif page == "マイページ（目標・AI相談）":
    st.header(f"📱 {user_info['name']} さんのマイページ")
    st.subheader("🤖 AIメンターへの自由相談")
    free_query = st.text_input("仕事の悩みなどを自由にどうぞ")
    if free_query:
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": free_query}])
        st.info(res.choices[0].message.content)

elif page == "管理者画面":
    st.header("🏆 人事査定シミュレーター")
    # 管理者用コードをここに集約