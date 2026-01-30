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

# --- 3. ログイン管理（コンパクト・中央寄せ・パスワード対応） ---
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
        
        input_id = st.text_input("社員IDを入力", key="login_input", placeholder="例: E001")
        input_pw = st.text_input("パスワードを入力", type="password", key="pw_input")
        
        if st.button("ログイン", use_container_width=True):
            if input_id in employee_master:
                # パスワードチェック (未設定の場合はデフォルト password123)
                correct_pw = employee_master[input_id].get("password", "password123")
                if input_pw == correct_pw:
                    st.session_state.login_id = input_id
                    st.rerun()
                else:
                    st.error("パスワードが正しくありません。")
            else:
                st.error("該当する社員IDが見つかりません。")
        st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()

# ユーザー情報の特定
user_info = employee_master[st.session_state.login_id]
user_name = user_info["name"]
dept_name = user_info["department"]

# --- 4. サイドバー表示（メニュー・ガイド・KPIの統合） ---
with st.sidebar:
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { background-color: #f8f9fa; }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
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
    
    page = st.radio("表示する画面を選択", menu_options)
    st.divider()

    if page == "振り返り対話":
        st.markdown("### 想定される会話の流れ")
        turns_desc = [
            ("① 共有", "報告"), ("② 深掘りI", "具体化"), ("③ 深掘りII", "検証"), ("④ 助言", "評価"), ("⑤ 目標", "確定")
        ]
        current_turn = st.session_state.get("turn_count", 1)
        for i, (t, _) in enumerate(turns_desc, 1):
            if i == current_turn: st.markdown(f"<p class='step-active'>👉 {t}</p>", unsafe_allow_html=True)
            elif i < current_turn: st.markdown(f"<p class='step-done'>✅ {t}</p>", unsafe_allow_html=True)
            else: st.markdown(f"<p class='step-inactive'>　 {t}</p>", unsafe_allow_html=True)

        st.divider()
        st.markdown(f"<div class='kpi-title'>{dept_name}のKPI</div>", unsafe_allow_html=True)
        current_kpis = kpi_data.get(dept_name, [])
        for k in current_kpis:
            st.markdown(f"<div class='kpi-item'>・{k}</div>", unsafe_allow_html=True)

    if st.button("ログアウト", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. メメイン画面表示エリア ---

if page == "振り返り対話":
    st.header("🌱 今日の一歩")
    st.write(f"**{user_name} さん / {dept_name}**")

    # --- 前回目標の要約抽出 ---
    conn = sqlite3.connect(get_file_path('kpi_app.db'))
    goal_df = pd.read_sql_query("SELECT content FROM messages WHERE employee_id=? AND role='assistant' AND content LIKE '%完了しました%' ORDER BY timestamp DESC LIMIT 1", conn, params=(st.session_state.login_id,))
    conn.close()
    
    if not goal_df.empty:
        raw_content = goal_df.iloc[0]['content']
        try:
            extraction_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "具体的な行動目標を1文で抜き出してください。目標のみを簡潔に示してください。"}, {"role": "user", "content": raw_content}]
            )
            summary = extraction_response.choices[0].message.content
            st.info(f"🎯 **前回の目標：{summary}**")
        except:
            st.info(f"🎯 **前回の目標：データの解析に失敗しました。**")
    else:
        st.write("設定された目標はまだありません。今日の振り返りで決めましょう！")

    st.info("""
        💡 週一回の共有を推奨していますが、アピールしたいことがあればいつでも共有OKです。  
        💡 共有が多いほど、アピールのチャンスとなります！  
        💡 課題やトラブルも共有してください。解決済みでも未解決でも大丈夫。今後どうしていくか一緒に考えましょう。
    """)

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "お疲れ様でした！今日の共有したいことは何ですか？"}]
        st.session_state.turn_count = 1

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.write(msg["content"])

    if prompt := st.chat_input("メッセージを入力..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)

        with st.chat_message("assistant"):
            turn = st.session_state.turn_count
            dept_kpis = "、".join(kpi_data.get(dept_name, []))
            system_prompt = f"あなたは{dept_name}のコーチです。KPI「{dept_kpis}」を基に対話してください。現在はターン {turn}/5 です。最後は必ず具体的な『次回の目標』を提示し、『今週の振り返りを完了しました』と締めてください。"
            response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}] + st.session_state.messages)
            ai_msg = response.choices[0].message.content
            st.write(ai_msg)
            st.session_state.messages.append({"role": "assistant", "content": ai_msg})

            conn = sqlite3.connect(get_file_path('kpi_app.db'))
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("INSERT INTO messages (employee_id, role, content, turn_count, timestamp) VALUES (?, ?, ?, ?, ?)", (st.session_state.login_id, "user", prompt, turn, now))
            conn.execute("INSERT INTO messages (employee_id, role, content, turn_count, timestamp) VALUES (?, ?, ?, ?, ?)", (st.session_state.login_id, "assistant", ai_msg, turn, now))
            conn.commit(); conn.close()
            if st.session_state.turn_count < 5: st.session_state.turn_count += 1; st.rerun()

elif page == "マイページ（目標・AI相談）":
    st.header(f"📱 {user_name} さんのマイページ")
    st.caption("🔒 このページの内容はあなた専用（非公開）です。")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎯 現在の目標")
        conn = sqlite3.connect(get_file_path('kpi_app.db'))
        goal_df = pd.read_sql_query("SELECT content FROM messages WHERE employee_id=? AND role='assistant' AND content LIKE '%完了しました%' ORDER BY timestamp DESC LIMIT 1", conn, params=(st.session_state.login_id,))
        conn.close()
        if not goal_df.empty: st.success(f"🎯 {goal_df.iloc[0]['content']}")
        
        st.subheader("📓 自分用メモ")
        st.text_area("気づきを記録（非公開）", height=200)

    with col2:
        st.subheader("🤖 AIメンターへの自由相談")
        query = st.text_input("仕事の悩みや相談をどうぞ")
        if query:
            with st.spinner("AIが回答中..."):
                res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": query}])
                st.info(res.choices[0].message.content)

elif page == "管理者画面":
    st.header("🏆 人事考課・査定支援ダッシュボード")
    st.caption("各担当者の振り返り内容を分析し、賞与（年2回）や昇格・昇進の評価材料を提供します。")

    try:
        conn = sqlite3.connect(get_file_path('kpi_app.db'))
        df = pd.read_sql_query("SELECT * FROM messages ORDER BY timestamp DESC", conn)
        conn.close()

        if df.empty:
            st.info("現在、社内に蓄積された対話ログはありません。")
        else:
            # 1. 課員の活動アクティビティ一覧
            st.subheader("👥 担当者の活動状況（最新順）")
            summary = df.groupby('employee_id').agg(last_active=('timestamp', 'max'), total_posts=('id', 'count')).reset_index()
            summary['name'] = summary['employee_id'].apply(lambda x: employee_master.get(x, {}).get('name', '不明'))
            summary['dept'] = summary['employee_id'].apply(lambda x: employee_master.get(x, {}).get('department', '不明'))
            
            st.dataframe(
                summary[['name', 'dept', 'total_posts', 'last_active']], 
                hide_index=True, use_container_width=True,
                column_config={"name": "氏名", "dept": "部署", "total_posts": "累計振り返り回数", "last_active": "最終更新日"}
            )

            st.divider()

            # 2. 個別査定レポート生成
            st.subheader("🧐 個別査定・昇進判断レポート")
            target_options = {eid: f"{info['name']} ({info['department']})" for eid, info in employee_master.items() if eid != "ADMIN01"}
            selected_eid = st.selectbox("分析する担当者を選択してください", options=list(target_options.keys()), format_func=lambda x: target_options[x])

            if selected_eid:
                t_logs = df[df['employee_id'] == selected_eid].sort_values('timestamp', ascending=True)
                
                # 目標履歴の確認
                with st.expander(f"📌 {employee_master[selected_eid]['name']} さんの目標履歴"):
                    goals = t_logs[t_logs['content'].str.contains('目標は|完了しました', na=False)]
                    st.dataframe(goals[['timestamp', 'content']], hide_index=True, use_container_width=True)

                if st.button(f"{employee_master[selected_eid]['name']} さんの評価レポートを生成"):
                    with st.spinner("これまでの全ログをAIがスキャン中..."):
                        all_log_text = "\n".join([f"{r['timestamp']} [{r['role']}]: {r['content']}" for _, r in t_logs.iterrows()])
                        t_dept = employee_master[selected_eid]['department']
                        kpi_list = "、".join(kpi_data.get(t_dept, ["全般的業務貢献"]))

                        prompt = f"""
                        あなたは公平な人事評価委員です。KPI「{kpi_list}」を基準にレポートを作成してください。
                        1. 普段の活動（量と質）
                        2. 目標達成のプロセス
                        3. トラブル対応能力
                        4. 賞与査定ランク案（S-D）と昇格への評価
                        """
                        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": all_log_text}])
                        st.success("AIレポートが完成しました。人事考課の参考資料としてください。")
                        st.markdown(res.choices[0].message.content)
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")