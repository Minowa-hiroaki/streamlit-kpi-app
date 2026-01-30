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
        with open(path, "r", encoding="utf-8") as f:  # ←ここをutf-8に
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
        .login-wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding-top: 10vh;
        }
        .login-content {
            width: 100%;
            max-width: 350px;
            text-align: left;
        }
        .login-content h2 { margin-bottom: 0px; }
        .login-content p { margin-bottom: 10px; font-size: 0.85rem; color: #666; }
        </style>
    """, unsafe_allow_html=True)

    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        st.markdown("<div class='login-wrapper'><div class='login-content'>", unsafe_allow_html=True)
        st.markdown("<h2>🌱 今日の一歩</h2>", unsafe_allow_html=True)
        st.markdown("<p>社員ログイン</p>", unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            input_id = st.text_input("社員ID", key="login_input", placeholder="例: E001")
            input_pw = st.text_input("パスワード", key="login_pw", type="password")
            submitted = st.form_submit_button("ログイン")
            if submitted:
                if input_id in employee_master:
                    user_info = employee_master[input_id]
                    pw_ok = str(user_info.get("password")) == str(input_pw)  # ←ここに修正
                    if pw_ok:
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

# パスワード再設定UI（サイドバー下部に表示）
def update_password(new_pw):
    import json
    employee_master[st.session_state.login_id]["password"] = new_pw
    with open(get_file_path("employee_master.json"), "w", encoding="utf-8") as f:  # ←ここもutf-8に
        json.dump(employee_master, f, ensure_ascii=False, indent=2)
    global employee_master
    employee_master = load_json_data("employee_master.json")  # ←再読込

with st.sidebar:
    st.markdown("---")
    with st.expander("パスワード再設定（本人のみ）"):
        new_pw = st.text_input("新しいパスワード", type="password", key="pw_reset")
        new_pw2 = st.text_input("新しいパスワード（確認）", type="password", key="pw_reset2")
        if st.button("パスワードを変更する"):
            if not new_pw:
                st.warning("新しいパスワードを入力してください。")
            elif new_pw != new_pw2:
                st.warning("パスワードが一致しません。")
            else:
                update_password(new_pw)
                st.success("パスワードを変更しました。次回ログインから新しいパスワードが有効です。")

 # --- 4. サイドバー表示（blue文字修正・スクロール対策） ---
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
    if current_kpis:
        for k in current_kpis:
            st.markdown(f"<div class='kpi-item'>・{k}</div>", unsafe_allow_html=True)
    else:
        st.caption("KPI未設定")
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
        default_idx = menu_options.index("管理者画面")
    else:
        default_idx = 0
    page = st.radio("表示する画面を選択", menu_options, index=default_idx)
    st.divider()


    # サイドバーでは画面切り替えUIのみ。ガイドやKPI表示はメイン画面分岐で行う。

    if st.button("ログアウト", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. メメイン画面表示エリア ---

if page == "振り返り対話":
    st.header("🌱 今日の一歩")
    st.write(f"**{user_name} さん / {dept_name}**")

    # --- 前回の目標をAIで抽出し表示（📌不要・要約ロジック強化） ---
    conn = sqlite3.connect(get_file_path('kpi_app.db'))
    goal_df = pd.read_sql_query(
        "SELECT content FROM messages WHERE employee_id=? AND role='assistant' AND content LIKE '%完了しました%' ORDER BY timestamp DESC LIMIT 1", 
        conn, params=(st.session_state.login_id,)
    )
    conn.close()
    
    if not goal_df.empty:
        raw_content = goal_df.iloc[0]['content']
        # 内部的にAIを使用して、目標となる一文のみを抽出する
        try:
            extraction_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "以下のコーチングメッセージから、コーチが提示した『次回の具体的な行動目標』にあたる1文だけを抜き出してください。余計な挨拶や「それでは」といった言葉は削除し、目標のみを簡潔に示してください。"},
                    {"role": "user", "content": raw_content}
                ]
            )
            summary = extraction_response.choices[0].message.content
            st.info(f"🎯 **前回の目標：{summary}**")
        except:
            # 抽出失敗時のフォールバック
            st.info(f"🎯 **前回の目標：目標データの解析に失敗しました。**")
    else:
        st.write("設定された目標はまだありません。今日の振り返りで決めましょう！")

    # --- ガイドメッセージ（改行入りで見やすく表示） ---
    st.info("""
        💡 週一回の共有を推奨していますが、アピールしたいことがあればいつでも共有OKです。  
        💡 共有が多いほど、アピールのチャンスとなります！  
        💡 課題やトラブルも共有してください。解決済みでも未解決でも大丈夫。今後どうしていくか一緒に考えましょう。
    """)

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "お疲れさまでした！今日の共有したいこと（売上、コスト、業務効率化、顧客満足度、トラブル）は何ですか？"}]
        st.session_state.turn_count = 1

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("メッセージを入力..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            turn = st.session_state.turn_count
            dept_kpis = "、".join(kpi_data.get(dept_name, []))

            system_prompt = f"""
            あなたは{dept_name}のコーチです。部署KPIは「{dept_kpis}」です。
            現在は【ターン {turn}/5】です。
            ターン5では必ず次週の目標をまとめ、「次回の目標は、[目標内容]です。それでは、今週の振り返りを完了しました。」と締めてください。
            """
            
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
            c.execute("INSERT INTO messages (employee_id, role, content, turn_count, timestamp) VALUES (?, ?, ?, ?, ?)",
                      (st.session_state.login_id, "user", prompt, turn, now))
            c.execute("INSERT INTO messages (employee_id, role, content, turn_count, timestamp) VALUES (?, ?, ?, ?, ?)",
                      (st.session_state.login_id, "assistant", ai_msg, turn, now))
            conn.commit()
            conn.close()

            if st.session_state.turn_count < 5:
                st.session_state.turn_count += 1
                st.rerun()

elif page == "マイページ（目標・AI相談）":
    st.header(f"📱 {user_name} さんのマイページ")
    st.caption("このページは本人のみ閲覧可能な非公開ページです。他のユーザーや管理者にも内容は表示されません。")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎯 現在の目標")
        conn = sqlite3.connect(get_file_path('kpi_app.db'))
        goal_df = pd.read_sql_query("SELECT content, timestamp FROM messages WHERE employee_id=? AND role='assistant' AND content LIKE '%完了しました%' ORDER BY timestamp DESC LIMIT 1", conn, params=(st.session_state.login_id,))
        conn.close()
        if not goal_df.empty:
            st.success(f"**設定日: {goal_df.iloc[0]['timestamp']}**\n\n🎯 {goal_df.iloc[0]['content']}")
        
        st.subheader("📓 自分用メモ")
        st.text_area("気づきを記録（非公開・一時保存）", height=200)
        st.button("メモを保存（デモ）")

    with col2:
        st.subheader("🤖 AIメンターへの自由相談（チャット形式・非公開）")
        if "mentor_chat" not in st.session_state:
            st.session_state.mentor_chat = [
                {"role": "assistant", "content": "こんにちは。どんなことでもご相談ください。"}
            ]
        for msg in st.session_state.mentor_chat:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        mentor_prompt = st.chat_input("AIメンターに相談する…")
        if mentor_prompt:
            st.session_state.mentor_chat.append({"role": "user", "content": mentor_prompt})
            with st.chat_message("user"):
                st.write(mentor_prompt)
            with st.chat_message("assistant"):
                with st.spinner("AIが回答中..."):
                    res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=st.session_state.mentor_chat
                    )
                    ai_reply = res.choices[0].message.content
                    st.write(ai_reply)
                    st.session_state.mentor_chat.append({"role": "assistant", "content": ai_reply})

elif page == "管理者画面":
    st.header("🏆 営業活動ダッシュボード（管理者用）")
    st.caption("各担当者の営業活動を一覧・分析し、人事考課の参考にできます。")
    try:
        conn = sqlite3.connect(get_file_path('kpi_app.db'))
        df = pd.read_sql_query("SELECT * FROM messages ORDER BY timestamp DESC", conn)
        conn.close()
        if df.empty:
            st.info("データが蓄積されていません。")
        else:
            # --- 1. 全担当者の活動サマリー ---

            st.subheader("👥 担当者別 活動サマリー")
            summary = df.groupby('employee_id').agg(
                last_active=('timestamp', 'max')
            ).reset_index()
            summary['name'] = summary['employee_id'].apply(lambda x: employee_master.get(x, {}).get('name', '不明'))
            summary['dept'] = summary['employee_id'].apply(lambda x: employee_master.get(x, {}).get('department', '不明'))
            # 活動内容要約（AIで生成）
            def get_activity_summary(eid):
                logs = df[df['employee_id']==eid].sort_values('timestamp', ascending=False).head(20)
                if logs.empty:
                    return "-"
                log_text = "\n".join([f"{r['timestamp']} [{r['role']}]: {r['content']}" for _, r in logs.iterrows()])
                prompt = f"""
                以下は営業担当者の最近の活動ログです。内容を簡潔に要約し、1ページ内で表記できる範囲（3～5行程度）でまとめてください。箇条書き推奨。
                {log_text}
                """
                try:
                    res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": prompt}]
                    )
                    return res.choices[0].message.content.strip()
                except:
                    return "要約取得エラー"
            summary['活動内容要約'] = summary['employee_id'].apply(get_activity_summary)
            # 活動内容要約をHTMLテーブルで折り返し表示
            st.markdown("""
                <style>
                .activity-summary-table { width: 100%; border-collapse: collapse; }
                .activity-summary-table th, .activity-summary-table td { border: 1px solid #ddd; padding: 8px; vertical-align: top; word-break: break-all; white-space: pre-line; }
                .activity-summary-table th { background: #f8f9fa; }
                </style>
            """, unsafe_allow_html=True)
            table_html = "<table class='activity-summary-table'>"
            table_html += "<tr><th>name</th><th>dept</th><th>last_active</th><th>活動内容要約</th></tr>"
            for _, row in summary.iterrows():
                table_html += f"<tr>"
                table_html += f"<td>{row['name']}</td>"
                table_html += f"<td>{row['dept']}</td>"
                table_html += f"<td>{row['last_active']}</td>"
                table_html += f"<td style='max-width:600px; word-break:break-all; white-space:pre-line'>{row['活動内容要約']}</td>"
                table_html += "</tr>"
            table_html += "</table>"
            st.markdown(table_html, unsafe_allow_html=True)

            st.divider()
            # --- 2. 個別担当者の詳細分析 ---
            st.subheader("🔍 個別担当者の詳細分析")
            target_opts = {eid: f"{info['name']} ({info['department']})" for eid, info in employee_master.items() if eid != "ADMIN01"}
            selected_eid = st.selectbox("分析する担当者を選択", options=list(target_opts.keys()), format_func=lambda x: target_opts[x])
            if selected_eid:
                t_logs = df[df['employee_id'] == selected_eid].sort_values('timestamp', ascending=True)
                st.markdown(f"### {employee_master[selected_eid]['name']} さんの活動履歴")

                st.dataframe(t_logs[['timestamp','role','content','turn_count']], hide_index=True, use_container_width=True)

                # 目標履歴（AI要約）
                with st.expander("📌 目標履歴（要約）"):
                    goals = t_logs[t_logs['content'].str.contains('目標は|完了しました', na=False)]
                    if not goals.empty:
                        goal_text = "\n".join(goals['content'].tolist())
                        prompt = f"""
                        以下は担当者の過去の目標履歴です。重複や挨拶を除き、ポイントを簡潔にまとめてください。1ページ内で表記できる範囲（3～5行程度）で要約してください。
                        {goal_text}
                        """
                        try:
                            res = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "system", "content": prompt}]
                            )
                            st.markdown(res.choices[0].message.content.strip())
                        except:
                            st.write("要約取得エラー")
                    else:
                        st.write("目標履歴がありません。")

                # AI評価案
                if st.button(f"{employee_master[selected_eid]['name']} さんのAI評価案を生成"):
                    with st.spinner("AIが活動を要約・評価中..."):
                        all_log_text = "\n".join([f"{r['timestamp']} [{r['role']}]: {r['content']}" for _, r in t_logs.iterrows()])
                        t_dept = employee_master[selected_eid]['department']
                        kpi_l = "、".join(kpi_data.get(t_dept, ["全般的貢献"]))
                        prompt = f"""
                        あなたは公平な人事評価委員です。以下のログに基づき、賞与（年2回）や昇進（年1回）の判断材料を作成してください。
                        【部署KPI】: {kpi_l}
                        【分析項目】:
                        1. 活動の具体性とKPIへの貢献
                        2. 課題発見・解決への姿勢
                        3. チーム貢献度
                        """
                        ai_res = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": prompt},
                                {"role": "user", "content": all_log_text}
                            ]
                        )
                        st.success("AI評価案：")
                        st.markdown(ai_res.choices[0].message.content)
    except Exception as e:
        st.error(f"データベース処理中にエラーが発生しました: {e}")
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