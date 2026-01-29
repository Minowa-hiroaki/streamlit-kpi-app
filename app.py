import streamlit as st
from openai import OpenAI
import sqlite3
import json
import os
import pandas as pd
import re
from datetime import datetime
from dotenv import load_dotenv

# --- 1. 環境設定 ---
load_dotenv()
st.set_page_config(page_title="今日の一歩", layout="wide")

# CSSによるレイアウト最適化（余白を削り上詰めにする）
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
    .stAlert { padding: 0.7rem; margin-bottom: 0.5rem; }
    div[data-testid="stExpander"] { margin-top: -1rem; }
    h1, h2, h3 { margin-top: 0rem; padding-top: 0rem; }
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

# --- 3. ログイン管理 ---
if "login_id" not in st.session_state:
    st.markdown("""
        <style>
        .login-wrapper { display: flex; flex-direction: column; align-items: center; justify-content: center; padding-top: 10vh; }
        .login-content { width: 100%; max-width: 350px; text-align: left; }
        .login-content h2 { margin-bottom: 0px; }
        .login-content p { margin-bottom: 10px; font-size: 0.85rem; color: #666; }
        </style>
    """, unsafe_allow_html=True)

    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        st.markdown("<div class='login-wrapper'><div class='login-content'>", unsafe_allow_html=True)
        st.markdown("<h2>🌱 今日の一歩</h2>", unsafe_allow_html=True)
        st.markdown("<p>社員ログイン</p>", unsafe_allow_html=True)
        input_id = st.text_input("社員IDを入力してEnterを押してください", key="login_input", placeholder="例: E001")
        if input_id:
            if input_id in employee_master:
                st.session_state.login_id = input_id
                st.rerun()
            else:
                st.error("該当する社員IDが見つかりません。")
        st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()

# ユーザー情報の特定
user_info = employee_master[st.session_state.login_id]
user_name = user_info["name"]
dept_name = user_info["department"]

# --- 4. サイドバー表示 ---
with st.sidebar:
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { background-color: #f8f9fa; }
        .step-active { color: #007bff; font-weight: bold; font-size: 0.9rem; margin-bottom: 0px; }
        .step-inactive { color: #6c757d; font-size: 0.85rem; margin-bottom: 0px; }
        .step-done { color: #adb5bd; text-decoration: line-through; font-size: 0.85rem; margin-bottom: 0px; }
        .step-desc { font-size: 0.72rem; color: #868e96; margin-left: 1.2rem; margin-bottom: 8px; line-height: 1.2; }
        .kpi-title { font-weight: bold; font-size: 0.95rem; margin-top: 1rem; margin-bottom: 0.5rem; }
        .kpi-item { font-size: 0.82rem; line-height: 1.4; margin-bottom: 6px; }
        hr { margin: 0.8rem 0 !important; }
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
                st.markdown(f"<div class='step-desc'>{desc}</div>", unsafe_allow_html=True)

        st.divider()
        st.markdown(f"<div class='kpi-title'>{dept_name}のKPI</div>", unsafe_allow_html=True)
        current_kpis = kpi_data.get(dept_name, [])
        for k in current_kpis:
            st.markdown(f"<div class='kpi-item'>・{k}</div>", unsafe_allow_html=True)

    if st.button("ログアウト", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. メイン画面表示エリア ---

if page == "振り返り対話":
    st.header("🌱 今日の一歩")
    st.write(f"**{user_name} さん / {dept_name}**")

    # --- 前回目標の自動抽出ロジック ---
    conn = sqlite3.connect(get_file_path('kpi_app.db'))
    goal_df = pd.read_sql_query(
        "SELECT content FROM messages WHERE employee_id=? AND role='assistant' AND content LIKE '%完了しました%' ORDER BY timestamp DESC LIMIT 1", 
        conn, params=(st.session_state.login_id,)
    )
    conn.close()
    
    if not goal_df.empty:
        full_text = goal_df.iloc[0]['content']
        # 目標抽出の正規表現: 「目標は、」と「。それでは」または「です。それでは」の間を抜き出す
        match = re.search(r"目標は、(.*?)(?:です|。)?(?=。それでは|それでは)", full_text)
        if match:
            summary = match.group(1).strip()
        else:
            # 抽出失敗時は最後から2番目の文を取得
            sentences = re.split(r'[。！]', full_text)
            summary = sentences[-2] if len(sentences) >= 2 else full_text
        st.info(f"🎯 **前回の目標：{summary}**")
    else:
        st.write("設定された目標はまだありません。今日の振り返りで決めましょう！")

    st.info("""
        💡 **週一回の共有を推奨していますが、アピールしたいことがあればいつでも共有OKです。** 💡 **共有が多いほど、アピールのチャンスとなります！** 💡 **課題やトラブルも共有してください。解決済みでも未解決でも大丈夫。今後どうしていくか一緒に考えましょう。**
    """)

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "お疲れさまでした！今日の共有したいこと（売上、コスト、業務効率化、顧客満足度、トラブル）は何ですか？"}]
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
            system_prompt = f"あなたは{dept_name}のコーチです。KPIは「{dept_kpis}」です。ターン {turn}/5 です。最後は必ず「次回の目標は、[具体的な目標]です。それでは、今週の振り返りを完了しました。」という形式で締めてください。"
            
            response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}] + st.session_state.messages)
            ai_msg = response.choices[0].message.content
            st.write(ai_msg)
            st.session_state.messages.append({"role": "assistant", "content": ai_msg})

            conn = sqlite3.connect(get_file_path('kpi_app.db'))
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("INSERT INTO messages (employee_id, role, content, turn_count, timestamp) VALUES (?, ?, ?, ?, ?)", (st.session_state.login_id, "user", prompt, turn, now))
            conn.execute("INSERT INTO messages (employee_id, role, content, turn_count, timestamp) VALUES (?, ?, ?, ?, ?)", (st.session_state.login_id, "assistant", ai_msg, turn, now))
            conn.commit(); conn.close()
            if st.session_state.turn_count < 5:
                st.session_state.turn_count += 1
                st.rerun()

elif page == "マイページ（目標・AI相談）":
    st.header(f"📱 {user_name} さんのマイページ")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎯 現在の目標")
        # マイページでも目標を要約して表示
        conn = sqlite3.connect(get_file_path('kpi_app.db'))
        goal_df = pd.read_sql_query("SELECT content, timestamp FROM messages WHERE employee_id=? AND role='assistant' AND content LIKE '%完了しました%' ORDER BY timestamp DESC LIMIT 1", conn, params=(st.session_state.login_id,))
        conn.close()
        if not goal_df.empty:
            full_t = goal_df.iloc[0]['content']
            match = re.search(r"目標は、(.*?)(?:です|。)?(?=。それでは|それでは)", full_t)
            sum_t = match.group(1).strip() if match else full_t
            st.success(f"**設定日: {goal_df.iloc[0]['timestamp']}**\n\n🎯 {sum_t}")
        
        st.subheader("📓 自分用メモ")
        st.text_area("気づきを記録（非公開・一時保存）", height=200)
        st.button("メモを保存（デモ）")

    with col2:
        st.subheader("🤖 AIメンターへの自由相談")
        query = st.text_input("仕事の悩みや相談をどうぞ")
        if query:
            with st.spinner("AIが回答中..."):
                res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": query}])
                st.info(res.choices[0].message.content)

elif page == "管理者画面":
    import pandas as pd
    st.header("🏆 人事査定・昇進シミュレーター")
    try:
        conn = sqlite3.connect(get_file_path('kpi_app.db'))
        df = pd.read_sql_query("SELECT * FROM messages ORDER BY timestamp DESC", conn)
        conn.close()
        if not df.empty:
            target_options = {eid: f"{info['name']} ({info['department']})" for eid, info in employee_master.items() if eid != "ADMIN01"}
            selected_eid = st.selectbox("査定する社員を選択", options=list(target_options.keys()), format_func=lambda x: target_options[x])
            t_logs = df[df['employee_id'] == selected_eid].sort_values('timestamp', ascending=True)
            if st.button("評価案を生成"):
                with st.spinner("分析中..."):
                    all_text = "\n".join([f"{row['role']}: {row['content']}" for _, row in t_logs.iterrows()])
                    res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": "人事評価者として分析して"}, {"role": "user", "content": all_text}])
                    st.markdown(res.choices[0].message.content)
            st.dataframe(t_logs)
    except Exception as e:
        st.error(f"データエラー: {e}")