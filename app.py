import streamlit as st
import pandas as pd
from datetime import date
from data_manager import DataManager
from streamlit_extras.let_it_rain import rain

# --- 設定とスタイリング ---
st.set_page_config(
    page_title="ふたりのWishlist & Calendar",
    page_icon="💑",
    layout="centered"
)

# 北欧モダン風のカスタムCSS（パステルカラーと清潔感）
st.markdown("""
<style>
    /* 全体のフォントと背景 */
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@300;400;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'M PLUS Rounded 1c', sans-serif;
    }
    
    .stApp {
        background-color: #FDFBF7; /* クリーム系の優しい白 */
    }
    
    /* 見出し */
    h1, h2, h3 {
        color: #5D6D7E; /* 落ち着いたグレー */
        font-weight: 700;
    }

    /* ボタン（共通） */
    div.stButton > button:first-child {
        background-color: #A9CCE3; /* パステルブルー */
        color: white;
        border-radius: 20px;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        background-color: #7FB3D5;
        transform: scale(1.05); /* ホバー時に少し拡大 */
    }
    
    /* 入力フィールド */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 1px solid #E5E7E9;
    }

    /* 提案カードのデザイン */
    .proposal-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border-left: 6px solid #ccc; /* デフォルトの色 */
    }
    .card-you { border-left-color: #AED6F1; } /* あなた（青） */
    .card-partner { border-left-color: #F5B7B1; } /* 彼女（ピンク） */

    /* バッジ */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 15px;
        color: white;
        font-size: 0.8rem;
        margin-right: 10px;
    }
    .bg-blue { background-color: #AED6F1; }
    .bg-pink { background-color: #F5B7B1; }
    .bg-cat { background-color: #D7BDE2; color: white; } /* カテゴリ用（紫） */

</style>
""", unsafe_allow_html=True)

# --- 認証機能 ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None

def check_password():
    """パスワード認証を行います。"""
    def_password = "1234"
    # secrets.tomlにパスワードがあればそれを使用
    if "general" in st.secrets and "password" in st.secrets["general"]:
        pwd = st.secrets["general"]["password"]
    else:
        pwd = def_password
    
    if st.session_state.password_input == pwd:
        st.session_state.authenticated = True
        del st.session_state.password_input # 入力値をクリア
    else:
        st.error("パスワードが違います 😢")

if not st.session_state.authenticated:
    st.title("🔐 ふたりのログイン")
    st.markdown("合言葉を入力してください")
    st.text_input("パスワード", type="password", key="password_input", on_change=check_password)
    st.stop() # 認証前はここで処理を止める

# --- ユーザー選択 ---
if not st.session_state.current_user:
    st.title("👤 あなたはどっち？")
    st.markdown("今日の担当を選んでください")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👦 あなた (Blue)", use_container_width=True):
            st.session_state.current_user = "あなた"
            st.rerun()
    with col2:
        if st.button("👧 彼女 (Pink)", use_container_width=True):
            st.session_state.current_user = "彼女"
            st.rerun()
    st.stop()

# --- メイン画面 ---
# サイドバー
st.sidebar.title(f"ようこそ、{st.session_state.current_user}さん")
st.sidebar.info("ふたりの思い出をここに記録しましょう。")
if st.sidebar.button("ログアウト"):
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.rerun()

# データマネージャーの初期化
db = DataManager()
if db.use_mock:
    st.sidebar.warning("⚠️ 現在モックモードで動作中（リロードでデータがリセットされます）")

st.title("✨ ふたりのWishlist & Calendar")

# タブ（機能切り替え）
tab_list, tab_add, tab_calendar = st.tabs(["📋 リスト & 承認", "➕ 新しい提案", "📅 カレンダー"])

# タブ1: 提案リストと承認
with tab_list:
    st.header("承認待ちの提案")
    df = db.fetch_data()
    
    if not df.empty:
        pending = df[df['status'] == 'pending']
        if pending.empty:
            st.info("承認待ちの提案はありません。新しいことを考えよう！")
        
        for idx, row in pending.iterrows():
            is_you = row['user'] == "あなた"
            # ユーザーごとのカードスタイル設定
            card_class = "card-you" if is_you else "card-partner"
            badge_class = "bg-blue" if is_you else "bg-pink"
            
            with st.container():
                st.markdown(f"""
                <div class="proposal-card {card_class}">
                    <h3>{row['title']}</h3>
                    <div style="margin-bottom: 10px;">
                        <span class="badge {badge_class}">{row['user']}</span>
                        <span class="badge bg-cat">{row['category']}</span>
                    </div>
                    <p style="color: #666;">希望日: {row['proposed_date'] if row['proposed_date'] else 'いつでもOK'}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 日付選択と承認ボタン
                c1, c2 = st.columns([2, 1])
                with c1:
                    d = st.date_input(f"実行する日を決める", date.today(), key=f"d_{row['id']}")
                with c2:
                    st.write("") # スペーサー
                    st.write("")
                    if st.button("これにする！承認 ❤️", key=f"b_{row['id']}"):
                        if db.approve_proposal(row['id'], d):
                            st.success("決定しました！")
                            # 紙吹雪エフェクト
                            rain(emoji="🎉", font_size=54, falling_speed=5, animation_length=1)
                            st.rerun()

# タブ2: 新規提案
with tab_add:
    st.header("新しい提案")
    with st.form("new_pitch"):
        f_title = st.text_input("やりたいこと / 行きたい場所")
        f_cat = st.radio("カテゴリ", ["旅行", "グルメ", "家", "日常"], horizontal=True)
        f_date = st.date_input("希望日 (あれば)", value=None)
        
        if st.form_submit_button("リストに追加する"):
            if f_title:
                if db.add_proposal(st.session_state.current_user, f_title, f_cat, f_date):
                    st.success("提案リストに追加しました！")
                    st.rerun()
            else:
                st.error("タイトルを入力してください")

# タブ3: カレンダー（確定リスト）
with tab_calendar:
    st.header("ふたりの予定表")
    if not df.empty:
        approved = df[df['status'] == 'approved'].copy()
        if approved.empty:
            st.info("まだ確定した予定はありません。")
        else:
            # 日付順にソート
            approved['scheduled_date'] = pd.to_datetime(approved['scheduled_date'])
            approved = approved.sort_values('scheduled_date')
            
            for idx, row in approved.iterrows():
                d_str = row['scheduled_date'].strftime('%Y年%m月%d日')
                st.markdown(f"### 🗓️ {d_str}")
                st.info(f"**{row['title']}** ({row['category']}) - 提案: {row['user']}")
    
    st.divider()
    # CSVダウンロード機能
    csv = df.to_csv(index=False).encode('utf-8_sig') # Windows向けにBOM付きUTF-8
    st.download_button("日付データをCSVで保存", csv, "our_plan.csv", "text/csv")
