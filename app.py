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

# CSSによるレイアウト最適化（余白を削り、極限まで上詰めにする）
st.markdown("""
    <style>
    /* メインエリアの上部余白を削除 */
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    /* サイドバーの上部余白を削除 */
    [data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
    /* エラートやインフォメーション枠の余白調整 */
    .stAlert { padding: 0.5rem 0.7rem; margin-bottom: 0.5rem; }
    /* ヘッダー周りの余白を最小化 */
    h1, h2, h3 { margin-top: 0rem; padding-top: 0rem; margin-bottom: 0.5rem; }
    /* チャット入力欄の固定位置調整 */
    .stChatInputContainer { padding-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

# APIキー設定
api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("APIキーが見つかりません。")
    st.stop()

client = OpenAI(api_key=api_key)

# --- 2. ユーティリティ関数 ---
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

# --- 3. ログイン管理（コンパクト・中央寄せ） ---
if "login_id" not in st.session_state:
    st.markdown("""
        <style>
        .login-wrapper { display: flex; flex-direction: column; align-items: center; justify-content: center; padding-top: 10vh; }
        .login-content { width: 100%; max-width: 350px; text-align: left; }
        </style>
    """, unsafe_allow_html=True)

    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        st.markdown("<div class='login-wrapper'><div class='login-content'>", unsafe_allow_html=True)
        st.markdown("<h2>🌱 今日の一歩</h2>", unsafe_allow_html=True)
        st.markdown("<p>社員ログイン</p>", unsafe_allow_html=True)
        input_id = st.text_input("社員IDを入力してEnter", key="login_input", placeholder="例: E001")
        if input_id:
            if input_id in employee_master:
                st.session_state.login_id = input_id
                st.rerun()
            else:
                st.error("該当する社員IDが見つかりません。")
        st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()

user_info = employee_master[st.session_state.login_id]
user_name = user_info["name"]
dept_name = user_info["department"]

# --- 4. サイドバー表示（上詰め設定） ---
with st.sidebar:
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { background-color: #f8f9fa; }
        .step-active { color: #007bff; font-weight: bold; font-size: 0.9rem; margin-bottom: 0px; }
        .step-inactive { color: #6c757d; font-size: 0.85rem; margin-bottom: 0px; }
        .step-done { color: #adb5bd; text-decoration: line-through; font-size: 0.85rem; margin-bottom: 0px; }
        .step-desc { font-size: 0.72rem; color: #868e96; margin-left: 1.2rem; margin-bottom: 8px; line-height: 1.2; }
        .kpi-title { font-weight: bold; font-size: 0.95rem; margin-top: 0.5rem; margin-bottom: 0.5rem; }
        .kpi-item { font-size: 0.82rem; line-height: 1.4; margin-bottom: 6px; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🌱 メニュー")
    menu_options = ["振り返り対話", "マイページ（目標・AI相談）"]
    if st.session_state.login_id == "ADMIN01":
        menu_options.append("管理者画面")
    
    page = st.radio("表示する画面を選択", menu_options, label_visibility="collapsed")
    st.divider()

    if page == "振り返り対話":
        st.markdown("### 想定される会話の流れ")
        turns_desc = [
            ("① 共有", "報告"), ("② 深掘りI", "具体化"), ("③ 深掘りII", "検証"), ("④ 助言", "KPI評価"), ("⑤ 目標", "確定")
        ]
        current_turn = st.session_state.get("turn_count", 1)
        for i, (t, desc) in enumerate(turns_desc, 1):
            if i == current_turn:
                st.markdown(f"<p class='step-active'>👉 {t}</p>", unsafe_allow_html=True)
            elif i < current_turn:
                st.markdown(f"<p class='step-done'>✅ {t}</p>", unsafe_allow_html=True)
            else:
                st.markdown(f"<p class='step-inactive'>　 {t}</p>", unsafe_allow_html=True)

        st.divider()
        st.markdown(f"<div class='kpi-title'>{dept_name}のKPI</div>", unsafe_allow_html=True)
        for k in kpi_data.get(dept_name, []):
            st.markdown(f"<div class='kpi-item'>・{k}</div>", unsafe_allow_html=True)

    if st.button("ログアウト", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. メイン画面エリア ---

if page == "振り返り対話":
    # タイトルとユーザー情報をコンパクトに表示
    st.subheader(f"🌱 今日の一歩 ({user_name} さん / {dept_name})")

    # --- 前回目標の要約抽出（AIによる再要約ロジック） ---
    conn = sqlite3.connect(get_file_path('kpi_app.db'))
    goal_df = pd.read_sql_query(
        "SELECT content FROM messages WHERE employee_id=? AND role='assistant' AND content LIKE '%完了しました%' ORDER BY timestamp DESC LIMIT 1", 
        conn, params=(st.session_state.login_id,)
    )
    conn.close()
    
    if not goal_df.empty:
        raw_text = goal_df.iloc[0]['content']
        # 目標部分だけを抽出させるための内部処理
        try:
            summary_res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "以下の文章から『次回の具体的な行動目標』となる1文だけを抜き出してください。余計な挨拶や締めの言葉は一切含めないでください。"},
                          {"role": "user", "content": raw_text}]
            )
            goal_summary = summary_res.choices[0].message.content
            st.info(f"🎯 **前回の目標：{goal_summary}**")
        except:
            st.info(f"🎯 **前回の目標：目標データを解析できませんでした。**")
    
    # ガイドメッセージの見やすい改行
    st.info("""
        💡 **週一回の共有を推奨していますが、アピールしたいことがあればいつでも共有OKです。** 💡 **共有が多いほど、アピールのチャンスとなります！** 💡 **課題やトラブルも共有してください。解決済みでも未解決でも大丈夫。今後どうしていくか一緒に考えましょう。**
    """)

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "お疲れさまでした！今週の出来事（売上、コスト、効率化、トラブル等）を教えてください。"}]
        st.session_state.turn_count = 1

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("メッセージを入力..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)

        with st.chat_message("assistant"):
            turn = st.session_state.turn_count
            dept_kpis = "、".join(kpi_data.get(dept_name, []))
            system_prompt = f"あなたは{dept_name}のコーチです。KPI「{dept_kpis}」を意識して対話してください。現在はターン {turn}/5 です。最後は必ず具体的な『次回の目標』を1文で提示し、『今週の振り返りを完了しました』と締めてください。"
            
            response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}] + st.session_state.messages)
            ai_msg = response.choices[0].message.content
            st.write(ai_msg)
            st.session_state.messages.append({"role": "assistant", "content": ai_msg})

            # DB保存
            conn = sqlite3.connect(get_file_path('kpi_app.db'))
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("INSERT INTO messages (employee_id, role, content, turn_count, timestamp) VALUES (?, ?, ?, ?, ?)", (st.session_state.login_id, "user", prompt, turn, now))
            conn.execute("INSERT INTO messages (employee_id, role, content, turn_count, timestamp) VALUES (?, ?, ?, ?, ?)", (st.session_state.login_id, "assistant", ai_msg, turn, now))
            conn.commit(); conn.close()

            if st.session_state.turn_count < 5:
                st.session_state.turn_count += 1
                st.rerun()

elif page == "マイページ（目標・AI相談）":
    st.subheader(f"📱 {user_name} さんのマイページ")
    # ... (マイページ用コード)