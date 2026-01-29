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
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, filename)

def load_json_data(filename):
    path = get_file_path(filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}

kpi_data = load_json_data("kpi_definitions.json")
employee_master = load_json_data("employee_master.json")

def init_db():
    conn = sqlite3.connect(get_file_path('kpi_app.db'))
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT, role TEXT, content TEXT, turn_count INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()
init_db()

# --- 3. ログイン管理 ---
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
user_name = user_info["name"]
dept_name = user_info["department"]

# --- 4. サイドバーメニュー（動的切り替え） ---
with st.sidebar:
    st.title("🌱 メニュー")
    menu_options = ["振り返り対話", "マイページ（目標・AI相談）"]
    if st.session_state.login_id == "ADMIN01":
        menu_options.append("管理者画面")
    
    page = st.radio("表示する画面を選択", menu_options)
    st.divider()
    
    if page == "振り返り対話":
        st.markdown(f"### 💡 {dept_name}のKPI")
        for k in kpi_data.get(dept_name, []):
            st.markdown(f"・{k}")

    if st.button("ログアウト", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. 画面切り替えロジック ---

# A. 振り返り対話画面
if page == "振り返り対話":
    st.header(f"💬 {user_name} さんの振り返り")
    
    # 前回の目標表示
    conn = sqlite3.connect(get_file_path('kpi_app.db'))
    goal_df = pd.read_sql_query("SELECT content FROM messages WHERE employee_id=? AND role='assistant' AND content LIKE '%完了しました%' ORDER BY timestamp DESC LIMIT 1", conn, params=(st.session_state.login_id,))
    conn.close()
    if not goal_df.empty:
        st.info(f"📌 **前回の目標:**\n{goal_df.iloc[0]['content']}")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "お疲れ様でした！今週の出来事は何ですか？"}]
        st.session_state.turn_count = 1

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.write(msg["content"])

    if prompt := st.chat_input("メッセージを入力..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        # AIレスポンス生成とDB保存のメイン処理（これまでのロジックを維持）
        # ... (詳細は省略していますが、基本構造は維持されます)
        st.rerun()

    
# B. マイページ画面
elif page == "マイページ（目標・AI相談）":
    # マイページ用にも目標データを取得
    conn = sqlite3.connect(get_file_path('kpi_app.db'))
    goal_df = pd.read_sql_query("SELECT content FROM messages WHERE employee_id=? AND role='assistant' AND content LIKE '%完了しました%' ORDER BY timestamp DESC LIMIT 1", conn, params=(st.session_state.login_id,))
    conn.close()
    st.header(f"📱 {user_name} さんのマイページ")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎯 現在の目標")
        # DBから最新の目標を再掲
        if not goal_df.empty:
            st.success(goal_df.iloc[0]['content'])
        
        st.subheader("📓 自分用メモ")
        st.text_area("気づきを記録（非公開）", height=200)
        st.button("メモを保存（デモ）")

    with col2:
        st.subheader("🤖 AIメンターへの自由相談")
        query = st.text_input("仕事の悩みや相談をどうぞ")
        if query:
            res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": query}])
            st.info(res.choices[0].message.content)

# C. 管理者画面
elif page == "管理者画面":
    st.header("🏆 人事査定・昇進シミュレーター")