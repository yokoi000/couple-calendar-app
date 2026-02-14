import streamlit as st
import pandas as pd
from datetime import date
from data_manager import DataManager
from streamlit_extras.let_it_rain import rain
import time

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
# タブ1: 提案リストと承認
with tab_list:
    # --- セクション1: ふたりのやりたいこと（承認待ち） ---
    st.markdown("### 💭 ふたりのやりたいこと (承認待ち)")
    st.caption("相手の提案に「いいね！」して、やりたいことリストに加えよう")
    
    df = db.fetch_data()
    
    if not df.empty:
        pending = df[df['status'] == 'pending']
        if pending.empty:
            st.info("承認待ちの提案はありません。")
        else:
            for idx, row in pending.iterrows():
                is_you = row['user'] == "あなた"
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
                        <p style="color: #666;">希望日: {row['proposed_date'] if row['proposed_date'] else '未定'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # ボタンエリア
                    col_btn, _2, _ = st.columns([1, 1, 2])
                    with col_btn:
                        if st.button("いいね！(承認) 👍", key=f"app_{row['id']}"):
                            if db.approve_proposal(row['id']):
                                st.success("承認しました！「いつやるか相談中」に移動します。")
                                rain(emoji="✨", font_size=54, falling_speed=5, animation_length=1)
                                st.rerun()
                    with _2:
                         # 編集ポップオーバー
                        with st.popover("✏️", help="編集"):
                            st.write("内容はここで修正できます")
                            with st.form(key=f"edit_form_{row['id']}"):
                                e_title = st.text_input("タイトル", value=row['title'])
                                e_cat = st.selectbox("カテゴリ", db.fetch_categories(), index=db.fetch_categories().index(row['category']) if row['category'] in db.fetch_categories() else 0)
                                e_date = st.date_input("希望日", value=pd.to_datetime(row['proposed_date']).date() if row['proposed_date'] else None)
                                
                                if st.form_submit_button("更新する"):
                                    updates = {
                                        "title": e_title,
                                        "category": e_cat,
                                        "proposed_date": e_date
                                    }
                                    if db.update_proposal(row['id'], updates):
                                        st.toast("更新しました！", icon="✅")
                                        time.sleep(1)
                                        st.rerun()

                        with st.popover("🗑️", help="削除"):
                            st.warning("この操作は取り消せません。本当に削除しますか？")
                            if st.button("削除", key=f"del_pending_{row['id']}", type="primary"):
                                if db.delete_proposal(row['id']):
                                    st.toast("削除しました", icon="🗑️")
                                    time.sleep(1)
                                    st.rerun()

    st.divider()

    # --- セクション2: いつやるか相談中（承認済み・日程未定） ---
    st.markdown("### 🗓️ いつやるか相談中")
    st.caption("ふたりで話し合って、実行する日を決めよう！")
    
    if not df.empty:
        approved = df[df['status'] == 'approved']
        if approved.empty:
            st.info("日程調整中の項目はありません。")
        else:
            for idx, row in approved.iterrows():
                # デザインは共通だが、ボーダー色を変えるなどで区別しても良い。今回は共通。
                is_you = row['user'] == "あなた"
                card_class = "card-you" if is_you else "card-partner"
                badge_class = "bg-blue" if is_you else "bg-pink"

                with st.container():
                    # シンプルなカード表示
                    st.markdown(f"""
                    <div class="proposal-card {card_class}" style="border-left-width: 10px;">
                        <h4>✅ {row['title']}</h4>
                        <div>
                            <span class="badge {badge_class}">{row['user']}</span>
                            <span class="badge bg-cat">{row['category']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 日付設定エリア
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        # デフォルトは今日、または希望日があればそこに近い日付
                        default_date = date.today()
                        if row['proposed_date']:
                            try:
                                default_date = pd.to_datetime(row['proposed_date']).date()
                            except:
                                pass
                        
                        d = st.date_input(f"実行日を決める", default_date, key=f"d_{row['id']}")
                    with c2:
                        st.write("") 
                        st.write("")
                        if st.button("カレンダーに登録 📅", key=f"sch_{row['id']}"):
                            if db.schedule_proposal(row['id'], d):
                                st.success("カレンダーに登録しました！")
                                rain(emoji="🎉", font_size=54, falling_speed=5, animation_length=1)
                                st.rerun()
                        
                        st.write("")
                        
                        # 編集機能
                        with st.popover("✏️", help="編集"):
                            st.write("内容を修正")
                            with st.form(key=f"edit_sched_{row['id']}"):
                                e_sched_title = st.text_input("タイトル", value=row['title'])
                                e_sched_cat = st.selectbox("カテゴリ", db.fetch_categories(), index=db.fetch_categories().index(row['category']) if row['category'] in db.fetch_categories() else 0)
                                if st.form_submit_button("更新"):
                                    if db.update_proposal(row['id'], {"title": e_sched_title, "category": e_sched_cat}):
                                        st.toast("更新しました！", icon="✅")
                                        time.sleep(1)
                                        st.rerun()

                        with st.popover("🗑️", help="削除"):
                            st.warning("この操作は取り消せません。本当に削除しますか？")
                            if st.button("削除", key=f"del_sched_{row['id']}", type="primary"):
                                if db.delete_proposal(row['id']):
                                    st.toast("削除しました", icon="🗑️")
                                    time.sleep(1)
                                    st.rerun()

# タブ2: 新規提案
# タブ2: 新規提案
with tab_add:
    st.header("新しい提案")
    # clear_on_submit=Trueで投稿後に自動リセット
    with st.form("new_pitch", clear_on_submit=True):
        f_title = st.text_input("やりたいこと / 行きたい場所")
        # カテゴリを動的に取得
        categories = db.fetch_categories()
        f_cat = st.radio("カテゴリ", categories, horizontal=True)
        
        f_date = st.date_input("希望日 (あれば)", value=None)
        
        if st.form_submit_button("リストに追加する"):
            if f_title:
                if db.add_proposal(st.session_state.current_user, f_title, f_cat, f_date):
                    st.toast("提案リストに追加しました！", icon="🎉")
                    time.sleep(1)
                    st.rerun()
            else:
                st.error("タイトルを入力してください")

# サイドバーにカテゴリ設定を移動
with st.sidebar.expander("⚙️ カテゴリ設定"):
    st.write("カテゴリの追加・編集")
    
    # カテゴリ追加
    st.subheader("追加")
    new_cat_name = st.text_input("新しいカテゴリ名", key="new_cat_input")
    if st.button("追加", key="add_cat_btn"):
        success, msg = db.add_category(new_cat_name)
        if success:
            st.success(msg)
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)
            
    st.divider()
    
    # カテゴリ編集
    st.subheader("名称変更")
    current_categories = db.fetch_categories()
    if current_categories:
        target_cat = st.selectbox("変更するカテゴリ", current_categories, key="edit_cat_target")
        
        # 影響範囲の計算
        all_data = db.fetch_data()
        impact_count = 0
        if not all_data.empty:
            impact_count = all_data[all_data['category'] == target_cat].shape[0]
        
        st.caption(f"※ 既存 **{impact_count}件** も更新")
        
        rename_cat_name = st.text_input("新しい名前", key="rename_cat_input")
        
        if st.button("変更を保存", key="rename_cat_btn"):
            success, msg = db.update_category(target_cat, rename_cat_name)
            if success:
                st.success(msg)
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)

# タブ3: カレンダー（確定リスト）
with tab_calendar:
    st.header("ふたりの予定表")
    if not df.empty:
        # 確定済み（scheduled）のみ表示
        approved = df[df['status'] == 'scheduled'].copy()
        if approved.empty:
            st.info("まだ確定した予定はありません。")
        else:
            # 日付順にソート
            approved['scheduled_date'] = pd.to_datetime(approved['scheduled_date'])
            approved = approved.sort_values('scheduled_date')
            
            for idx, row in approved.iterrows():
                d_str = row['scheduled_date'].strftime('%Y年%m月%d日')
                st.markdown(f"### 🗓️ {d_str}")
                
                c_info, c_del = st.columns([4, 1])
                with c_info:
                    st.info(f"**{row['title']}** ({row['category']}) - 提案: {row['user']}")
                with c_del:
                    with st.popover("🗑️", help="削除"):
                        st.warning("この操作は取り消せません。本当に削除しますか？")
                        if st.button("削除", key=f"del_cal_{row['id']}", type="primary"):
                            if db.delete_proposal(row['id']):
                                st.toast("削除しました", icon="🗑️")
                                time.sleep(1)
                                st.rerun()
    
    st.divider()
    # CSVダウンロード機能
    csv = df.to_csv(index=False).encode('utf-8_sig') # Windows向けにBOM付きUTF-8
    st.download_button("日付データをCSVで保存", csv, "our_plan.csv", "text/csv")
