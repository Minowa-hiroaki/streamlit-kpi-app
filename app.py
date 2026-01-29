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
            st.session_state.turn_count = 1
            st.rerun()
        else:
            st.error("IDが正しくありません")
    st.stop()

user_info = employee_master[st.session_state.login_id]
user_name = user_info["name"]
dept_name = user_info["department"]

# --- 4. サイドバー（メニューとガイドを完全復元） ---
with st.sidebar:
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { background-color: #f8f9fa; }
        .step-active { color: #007bff; font-weight: bold; font-size: 0.9rem; }
        .step-inactive { color: #6c757d; font-size: 0.85rem; }
        .step-done { color: #adb5bd; text-decoration: line-through; font-size: 0.85rem; }
        .step-desc { font-size: 0.72rem; color: #868e96; margin-left: 1.2rem; margin-bottom: 8px; line-height: 1.2; }
        .kpi-title { font-weight: bold; font-size: 0.95rem; margin-top: 1rem; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🌱 メニュー")
    menu_options = ["振り返り対話", "マイページ（目標・AI相談）"]
    if st.session_state.login_id == "ADMIN01":
        menu_options.append("管理者画面")
    
    page = st.radio("表示する画面を選択", menu_options)
    st.divider()

    # 「振り返り対話」の時のみ、詳細ガイドを表示
    if page == "振り返り対話":
        st.markdown("### 想定される会話の流れ")
        turns_desc = [
            ("① 共有", "今週の出来事を報告"),
            ("② 深掘りI", "行動や数値を具体化"),
            ("③ 深掘りII", "リスクや懸念の検証"),
            ("④ フィードバック", "KPI視点での助言"),
            ("⑤ 次の目標", "来週の目標を確定")
        ]
        
        current_turn = st.session_state.get("turn_count", 1)
        for i, (t, desc) in enumerate(turns_desc, 1):
            if i == current_turn:
                st.markdown(f"<p class='step-active'>👉 {t}</p>", unsafe_allow_html=True)
                st.markdown(f"<div class='step-desc'>{desc}</div>", unsafe_allow_html=True)
            elif i < current_turn:
                st.markdown(f"<p class='step-done'>✅ {t}</p>", unsafe_allow_html=True)
            else:
                st.markdown(f"<p class='step-inactive'>　 {t}</p>", unsafe_allow_html=True)

        st.divider()
        st.markdown(f"<div class='kpi-title'>{dept_name}のKPI</div>", unsafe_allow_html=True)
        for k in kpi_data.get(dept_name, []):
            st.markdown(f"・{k}")

    st.divider()
    if st.button("ログアウト", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. メイン表示エリア ---

if page == "振り返り対話":
    st.header(f"💬 {user_name} さんの振り返り")
    
    # 前回の目標表示
    conn = sqlite3.connect(get_file_path('kpi_app.db'))
    goal_df = pd.read_sql_query("SELECT content FROM messages WHERE employee_id=? AND role='assistant' AND content LIKE '%完了しました%' ORDER BY timestamp DESC LIMIT 1", conn, params=(st.session_state.login_id,))
    conn.close()
    if not goal_df.empty:
        st.info(f"📌 **前回の目標:**\n{goal_df.iloc[0]['content']}")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "お疲れさまでした！今週の出来事は何ですか？"}]
        st.session_state.turn_count = 1

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.write(msg["content"])

    if prompt := st.chat_input("メッセージを入力..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            turn = st.session_state.turn_count
            dept_kpis = "、".join(kpi_data.get(dept_name, []))
            
            system_prompt = f"""あなたは{dept_name}のコーチです。全5ターンの現在は【ターン {turn}】です。
            KPI「{dept_kpis}」を意識した質問をしてください。最後は必ず次週の目標をまとめ、『完了しました』と述べてください。"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt}] + st.session_state.messages
            )
            ai_msg = response.choices[0].message.content
            st.write(ai_msg)
            st.session_state.messages.append({"role": "assistant", "content": ai_msg})

            # DB保存
            conn = sqlite3.connect(get_file_path('kpi_app.db'))
            c = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO messages (employee_id, role, content, turn_count, timestamp) VALUES (?, ?, ?, ?, ?)", (st.session_state.login_id, "user", prompt, turn, now))
            c.execute("INSERT INTO messages (employee_id, role, content, turn_count, timestamp) VALUES (?, ?, ?, ?, ?)", (st.session_state.login_id, "assistant", ai_msg, turn, now))
            conn.commit()
            conn.close()

            if st.session_state.turn_count < 5:
                st.session_state.turn_count += 1
            st.rerun()

elif page == "マイページ（目標・AI相談）":
    st.header(f"📱 {user_name} さんのマイページ")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎯 現在の目標")
        # 前回の完了メッセージを再掲
        conn = sqlite3.connect(get_file_path('kpi_app.db'))
        goal_df = pd.read_sql_query("SELECT content, timestamp FROM messages WHERE employee_id=? AND role='assistant' AND content LIKE '%完了しました%' ORDER BY timestamp DESC LIMIT 1", conn, params=(st.session_state.login_id,))
        conn.close()
        if not goal_df.empty:
            st.success(f"**設定日: {goal_df.iloc[0]['timestamp']}**\n\n{goal_df.iloc[0]['content']}")
        
        st.subheader("📓 自分用成長メモ")
        st.text_area("気づきを記録（自分専用）", height=200)
        st.button("メモを保存（デモ）")

    with col2:
        st.subheader("🤖 AIメンターへの自由相談")
        query = st.text_input("仕事の悩みや相談をどうぞ")
        if query:
            res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": query}])
            st.info(res.choices[0].message.content)

elif page == "管理者画面":
    st.header("🏆 人事査定・昇進シミュレーター")
    # 管理者用コードを配置（以前のAdminロジック）