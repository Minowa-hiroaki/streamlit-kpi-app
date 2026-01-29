import streamlit as st
from openai import OpenAI
import sqlite3
import json
import os
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
# kpis という別名も用意（管理者画面のコード互換のため）
kpis = kpi_data

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

# --- 4. サイドバー（メニュー切り替えと連動） ---
# ここにサイドバーの内容をまとめます
with st.sidebar:
    st.title("🌱 メニュー")
    
    # ログイン中のみメニューを表示
    if "login_id" in st.session_state:
        # メニューの選択肢を作成
        menu_options = ["振り返り対話", "マイページ（目標・AI相談）"]
        if st.session_state.login_id == "ADMIN01":
            menu_options.append("管理者画面")
        
        # ★ここでラジオボタンを表示。これが出ない原因の多くは、このコードが実行される前にst.stop()が入っているせいです
        page = st.radio("表示する画面を選択", menu_options, key="main_menu")
        
        st.divider()

        # 「振り返り対話」の時だけガイドを表示
        if page == "振り返り対話":
            st.markdown("### 想定される会話の流れ")
            st.caption("①共有 → ②深掘り → ③リスク検証 → ④評価 → ⑤目標確定")
            st.divider()
            st.markdown(f"**{dept_name}のKPI**")
            for k in kpi_data.get(dept_name, []):
                st.markdown(f"・{k}")

        st.divider()
        if st.button("ログアウト", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    else:
        st.write("ログインしてください")

# --- 5. メイン画面の表示切り替え ---
# サイドバーで選んだ 'page' の値によって、表示する中身を分岐させます

if page == "振り返り対話":
    # これまでのチャット画面のコードをここに
    st.header(f"💬 {user_name} さんの振り返り")
    # ...（中略）...

elif page == "マイページ（目標・AI相談）":
    # マイページのコードをここに
    st.header(f"📱 {user_name} さんのマイページ")
    # ...（中略）...

elif page == "管理者画面":
    # 管理者画面のコードをここに
    # ...

    # ログアウトボタンを一番下に配置
    if st.button("ログアウト", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. メイン画面の表示切り替え ---

# 【振り返り対話】画面
if page == "振り返り対話":
    st.header("💬 今週の振り返り")
    # ...（これまでの対話用コードをここに配置）...

# 【マイページ】画面
elif page == "マイページ（目標・AI相談）":
    st.header(f"📱 {user_name} さんのマイページ")
    # ...（前回のマイページ用コードをここに配置）...

# 【管理者画面】
# 【管理者画面】
elif page == "管理者画面":
    # ...（管理者用コードをここに配置）...
    pass
# --- 5. メイン画面レイアウト ---
# 不要なコードを削除（インデントエラー解消）

st.write(f"**{user_name} さん / {dept_name}**")

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

if prompt := st.chat_input("メッセージを入力してEnterで送信"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        turn = st.session_state.turn_count
        dept_kpis = "、".join(kpi_data.get(dept_name, []))

        # --- AIへの指示をより厳格に修正 ---
        system_prompt = f"""
        あなたは{dept_name}のコーチです。部署KPIは「{dept_kpis}」です。
        全5ターンの対話フローのうち、現在は【ターン {turn}】です。
        
        【各ターンの厳守ルール】
        ターン1: 共有（済）
        ターン2: 深掘りI（行動や数値の具体化） -> 具体的な「数字」や「行動内容」を1つだけ聞く。
        ターン3: 深掘りII（リスク検証） -> 「もし〜だったら？」という視点で、懸念点やリスクを1つだけ聞く。
        ターン4: フィードバック（KPI評価） -> ここまでの内容を整理し、KPIに照らして評価し、具体的な助言をする（質問はしない）。
        ターン5: 次の目標（完了） -> 次の目標を1つ確認し、最後に必ず「今週の振り返りを完了しました」と述べて対話を締める。

        【共通ルール】
        - 常に優しく、前向きなトーンで。
        - ターンに応じた発言を1回につき1つだけしてください。
        - 前のターンの役割を繰り返さないでください。
        """
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}] + st.session_state.messages
        )
        ai_msg = response.choices[0].message.content
        st.write(ai_msg)
        st.session_state.messages.append({"role": "assistant", "content": ai_msg})

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

# --- 6. 管理者専用セクション（ここから最後まで入れ替え） ---

# ログインしているIDが ADMIN01 の場合のみ、以下の処理を実行する
if "login_id" in st.session_state and st.session_state.login_id == "ADMIN01":
    import pandas as pd

    st.divider()
    st.header("🏆 人事査定・昇進シミュレーター")

    # データの読み込み：ADMIN01の時だけ実行されるので一般社員時にエラーになりません
    try:
        conn = sqlite3.connect(get_file_path('kpi_app.db'))
        # messagesテーブルから全データを取得
        df = pd.read_sql_query("SELECT * FROM messages ORDER BY timestamp DESC", conn)
        conn.close()
    except Exception as e:
        st.error(f"データベースの読み込みに失敗しました: {e}")
        df = pd.DataFrame() # 空のデータフレームを作成して後続のエラーを防ぐ

    if not df.empty:
        # 査定対象の社員リストを作成（自分以外）
        target_options = {eid: f"{info['name']} ({info['department']})" 
                         for eid, info in employee_master.items() if eid != "ADMIN01"}
        
        selected_eid = st.selectbox(
            "査定する社員を選択してください", 
            options=list(target_options.keys()), 
            format_func=lambda x: target_options[x]
        )

        # 選択された社員のログを抽出
        target_logs = df[df['employee_id'] == selected_eid].sort_values('timestamp', ascending=True)
        
        if not target_logs.empty:
            st.subheader(f"📈 {employee_master[selected_eid]['name']} さんの成長ログ")
            
            # AI査定支援レポート生成ボタン
            if st.button(f"{employee_master[selected_eid]['name']} さんの評価案を生成"):
                with st.spinner("これまでの対話ログをAIが分析中..."):
                    # ログをテキストに変換
                    all_text = "\n".join([f"{row['timestamp']} [{row['role']}]: {row['content']}" for _, row in target_logs.iterrows()])
                    
                    # 部署ごとのKPI定義を取得
                    dept_name = employee_master[selected_eid]['department']
                    kpi_info = kpis.get(dept_name, "全般的な業務貢献")

                    review_response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": f"あなたは公平な人事評価委員です。部署KPI「{kpi_info}」を基準に、賞与査定と昇進の判断材料を作成してください。"},
                            {"role": "user", "content": f"以下のログを分析し、1.主な成果、2.KPI貢献度、3.次期の課題、4.査定ランク案(S-D)を出力してください。\n\n{all_text}"}
                        ]
                    )
                    st.success("AI評価レポートが生成されました")
                    st.markdown(review_response.choices[0].message.content)

            # 詳細なやり取り履歴を確認できるアコーディオン
            with st.expander("詳細な対話履歴（全件）"):
                st.dataframe(target_logs[['timestamp', 'role', 'content', 'turn_count']], use_container_width=True)
                
                # CSVダウンロード機能
                csv = target_logs.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="この社員のログをCSVで保存",
                    data=csv,
                    file_name=f"log_{selected_eid}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )
        else:
            st.info(f"{employee_master[selected_eid]['name']} さんの記録はまだありません。")
    else:
        st.info("現在、社内に蓄積された対話ログはありません。")

# --- サイドバーによるメニュー切り替え ---
with st.sidebar:
    st.title("メニュー")
    # 管理者の場合は管理者画面も選択肢に出す
    menu_options = ["振り返り対話", "マイページ（目標・メモ）"]
    if st.session_state.get("login_id") == "ADMIN01":
        menu_options.append("管理者画面")
    
    page = st.radio("表示する画面を選択", menu_options)
    st.divider()
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()

# --- 各画面の処理 ---

# どの画面でも使う「前回の目標」取得（pandasが必要なのでimportも保証）
import pandas as pd
conn = sqlite3.connect(get_file_path('kpi_app.db'))
prev_goal = pd.read_sql_query(
    "SELECT content FROM messages WHERE employee_id=? AND role='assistant' AND content LIKE '%【次回の目標】%' ORDER BY timestamp DESC LIMIT 1",
    conn, params=(st.session_state.login_id,)
)
conn.close()

# 1. 振り返り対話画面
if page == "振り返り対話":
    st.header(f"💬 {user_info['name']} さんの今週の振り返り")
    
    # 【追加機能】前回の目標を画面上部に表示しておく
    with st.expander("前回の目標を確認する", expanded=True):
        if not prev_goal.empty:
            st.info(prev_goal.iloc[0]['content'])
        else:
            st.write("設定された目標はまだありません。今日の振り返りで決めましょう！")

    # （ここから下に、これまでの対話チャット機能が続きます）

# 2. マイページ（目標・メモ・AI相談）
elif page == "マイページ（目標・メモ）":
    st.header(f"📱 {user_info['name']} さんのマイページ")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 現在の目標と指針")
        # 前回の目標とAIのアドバイスを再掲
        if not prev_goal.empty:
            st.success(prev_goal.iloc[0]['content'])
        
        st.subheader("📓 自分の成長メモ")
        st.text_area("自分だけの気づきを記録（他の人には見えません）", height=200, placeholder="今週気づいたことや、次の面談で話したいことなど...")
        st.button("メモを保存（デモ）")

    with col2:
        st.subheader("🤖 AIメンターに自由相談")
        st.caption("振り返り以外でも、仕事の悩みやスキルアップについて相談できます。")
        free_query = st.text_input("AIに質問する（例：効率的なタスク管理の方法は？）")
        if free_query:
            with st.spinner("AIが回答を生成中..."):
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": free_query}]
                )
                st.chat_message("assistant").write(res.choices[0].message.content)

# 3. 管理者画面（ADMIN01のみ）
elif page == "管理者画面":
    # （ここに以前作成した管理者用コードを配置します）
    pass