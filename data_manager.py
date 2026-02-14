import streamlit as st
import pandas as pd
import datetime
from datetime import date

# gspreadがインストールされていない、または設定されていない場合のハンドリング
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

# LINE SDK Import (try-except to avoid error if not installed locally)
try:
    from linebot import LineBotApi
    from linebot.models import TextSendMessage
    HAS_LINE_SDK = True
except ImportError:
    HAS_LINE_SDK = False

# キャッシュされた接続関数
@st.cache_resource
def get_gspread_client(creds_dict):
    """
    gspreadクライアントをキャッシュして返す関数
    """
    return gspread.service_account_from_dict(creds_dict)

@st.cache_data(ttl=600)
def _get_categories_from_sheet(creds_dict, spreadsheet_url):
    """categoriesシートからデータを取得（キャッシュ付き）"""
    try:
        gc = gspread.service_account_from_dict(creds_dict)
        wb = gc.open_by_url(spreadsheet_url)
        ws = wb.worksheet("categories")
        return ws.col_values(1)
    except Exception as e:
        print(f"Categories fetch error: {e}")
        return None

class DataManager:
    """
    データの取得・保存を行うクラス。
    Google Sheetsとの連携を管理し、開発/本番環境の切り替えを行います。
    """
    def __init__(self):
        self.use_mock = True
        self.sheet = None
        self._initialize_connection()

    def _initialize_connection(self):
        """
        secrets.tomlの設定を使ってGoogle Sheetsへの接続を試みます。
        """
        if not HAS_GSPREAD:
            print("gspreadライブラリが見つかりません。モックモードで動作します。")
            self.use_mock = True
            self._init_mock_data()
            return

        try:
            # GCP認証情報の取得
            if "gcp_service_account" not in st.secrets:
                raise ValueError("Secretsにgcp_service_accountがありません")
            
            creds_dict = dict(st.secrets["gcp_service_account"])
            gc = get_gspread_client(creds_dict)

            # 環境に応じたURLの取得
            env = st.secrets.get("env", {}).get("current", "dev") # デフォルトはdev
            url_key = f"spreadsheet_url_{env}"
            
            if "google_sheets" not in st.secrets or url_key not in st.secrets["google_sheets"]:
                raise ValueError(f"Secretsに{url_key}が設定されていません")
            
            spreadsheet_url = st.secrets["google_sheets"][url_key]
            
            # シートを開く
            self.sheet = gc.open_by_url(spreadsheet_url).sheet1
            self.use_mock = False
            
            # ヘッダーの自動初期化チェック
            self._check_and_init_header()
            
            print(f"Google Sheets ({env}) に接続しました。")

        except Exception as e:
            print(f"Google Sheetsへの接続に失敗しました: {e}。モックモードで動作します。")
            self.use_mock = True
            self._init_mock_data()

    def _check_and_init_header(self):
        """
        シートが空の場合、ヘッダーを書き込みます。
        """
        try:
            if not self.sheet.get_all_values():
                headers = ["id", "user", "title", "category", "proposed_date", "status", "created_at", "scheduled_date"]
                self.sheet.append_row(headers)
                print("ヘッダーを初期化しました。")
        except Exception as e:
            print(f"ヘッダー初期化エラー: {e}")

    def _init_mock_data(self):
        """モックデータの初期化"""
        if "mock_db" not in st.session_state:
            st.session_state.mock_db = pd.DataFrame(columns=[
                "id", "user", "title", "category", "proposed_date", "status", "created_at", "scheduled_date"
            ])
            # デモデータ
            dummy_data = [
                {"id": "1", "user": "あなた", "title": "北海道旅行に行きたい", "category": "旅行", "proposed_date": "2024-05-01", "status": "pending", "created_at": datetime.datetime.now().isoformat(), "scheduled_date": ""},
                {"id": "2", "user": "彼女", "title": "新しいソファを見る", "category": "家", "proposed_date": "2024-02-20", "status": "approved", "created_at": datetime.datetime.now().isoformat(), "scheduled_date": ""},
            ]
            st.session_state.mock_db = pd.concat([st.session_state.mock_db, pd.DataFrame(dummy_data)], ignore_index=True)
            
        if "mock_categories" not in st.session_state:
            st.session_state.mock_categories = ["旅行", "グルメ", "家", "日常"]

    def fetch_data(self):
        """データを取得"""
        if self.use_mock:
            return st.session_state.mock_db
        else:
            try:
                # get_all_valuesで全データをリストとして取得（ヘッダーエラー回避のため）
                rows = self.sheet.get_all_values()
                
                # 必須カラムの定義
                expected_cols = ["id", "user", "title", "category", "proposed_date", "status", "created_at", "scheduled_date"]
                
                if len(rows) < 2:
                    # ヘッダーのみ、または空の場合は空のDataFrameを返す
                    return pd.DataFrame(columns=expected_cols)
                
                # ヘッダー行(rows[0])は無視して、データ行(rows[1:])を使用
                data_rows = rows[1:]
                
                # 列数が足りない場合は空文字で埋める、多い場合は切り捨てる
                cleaned_data = []
                for row in data_rows:
                    if len(row) < len(expected_cols):
                        # 足りない分を空文字で埋める
                        row += [""] * (len(expected_cols) - len(row))
                    elif len(row) > len(expected_cols):
                        # 多い分は切り捨てる
                        row = row[:len(expected_cols)]
                    cleaned_data.append(row)
                
                df = pd.DataFrame(cleaned_data, columns=expected_cols)
                return df
            except Exception as e:
                st.error(f"データ取得エラー: {e}")
                return pd.DataFrame(columns=["id", "user", "title", "category", "proposed_date", "status", "created_at", "scheduled_date"])

    def add_proposal(self, user, title, category, proposed_date=""):
        """新規提案の追加 (Status: pending)"""
        new_row = {
            "id": str(datetime.datetime.now().timestamp()),
            "user": user,
            "title": title,
            "category": category,
            "proposed_date": str(proposed_date) if proposed_date else "",
            "status": "pending",
            "created_at": datetime.datetime.now().isoformat(),
            "scheduled_date": ""
        }

        if self.use_mock:
            st.session_state.mock_db = pd.concat([st.session_state.mock_db, pd.DataFrame([new_row])], ignore_index=True)
            self.send_line_notification(f"[新しい提案] {user}さんが『{title}』を提案しました！💑\nアプリを開く: https://couple-calendar-app.streamlit.app/")
            return True
        else:
            try:
                # 辞書の順序はヘッダーと一致させる必要がありますが、gspreadのappend_rowはリストを受け取ります
                # ここでは辞書のキー順ではなく、明示的なリストを作成します
                values = [
                    new_row["id"], new_row["user"], new_row["title"], new_row["category"], 
                    new_row["proposed_date"], new_row["status"], new_row["created_at"], new_row["scheduled_date"]
                ]
                self.sheet.append_row(values)
                
                # LINE通知
                self.send_line_notification(f"[新しい提案] {user}さんが『{title}』を提案しました！💑\nアプリを開く: https://couple-calendar-app.streamlit.app/")
                
                return True
            except Exception as e:
                st.error(f"追加エラー: {e}")
                return False

    def approve_proposal(self, item_id, title=""): # title引数を追加して通知に使う
        """提案承認 (Status: pending -> approved)"""
        # titleが渡されていない場合は取得するロジックが必要だが、簡略化のため呼び出し元で渡すか、ここで検索するか。
        # ここでは検索コストを避けるため、呼び出し元で渡してもらうように変更するのがベストだが、既存コードへの影響を最小限にするため、
        # 必要な場合のみ検索、または通知メッセージを汎用的にする。
        # 今回は、通知のためにtitleが必要なので、モック/DBから取得する。
        
        target_title = title
        
        if self.use_mock:
            df = st.session_state.mock_db
            idx = df[df['id'] == item_id].index
            if not idx.empty:
                st.session_state.mock_db.at[idx[0], 'status'] = 'approved'
                target_title = st.session_state.mock_db.at[idx[0], 'title']
                self.send_line_notification(f"[承認] {target_title} が承認されました！✨ 二人で日程を決めよう！\nアプリを開く: https://couple-calendar-app.streamlit.app/")
                return True
            return False
        else:
            try:
                cell = self.sheet.find(str(item_id))
                if cell:
                    # statusカラムは6番目 (F列) と仮定
                    # ヘッダー: id(1), user(2), title(3), category(4), proposed_date(5), status(6), created_at(7), scheduled_date(8)
                    self.sheet.update_cell(cell.row, 6, "approved")
                    
                    # タイトルを取得 (3列目)
                    if not target_title:
                         target_title = self.sheet.cell(cell.row, 3).value

                    self.send_line_notification(f"[承認] {target_title} が承認されました！✨ 二人で日程を決めよう！\nアプリを開く: https://couple-calendar-app.streamlit.app/")
                    return True
                return False
            except Exception as e:
                st.error(f"承認エラー: {e}")
                return False

    def send_line_notification(self, message):
        """LINE Messaging APIで通知を送信"""
        if not HAS_LINE_SDK:
            return

        try:
            # フラットなキー名で取得
            token = st.secrets.get("LINE_CHANNEL_ACCESS_TOKEN")
            user_id = st.secrets.get("LINE_USER_ID") # または LINE_GROUP_ID
            
            if not token or not user_id:
                # 設定がない場合は何もしない
                return

            line_bot_api = LineBotApi(token)
            line_bot_api.push_message(user_id, TextSendMessage(text=message))
            
        except Exception as e:
            # 通知エラーでアプリを止めない
            print(f"LINE通知エラー: {e}")

    def schedule_proposal(self, item_id, scheduled_date):
        """日程確定 (Status: approved -> scheduled)"""
        if self.use_mock:
            df = st.session_state.mock_db
            idx = df[df['id'] == item_id].index
            if not idx.empty:
                st.session_state.mock_db.at[idx[0], 'status'] = 'scheduled'
                st.session_state.mock_db.at[idx[0], 'scheduled_date'] = str(scheduled_date)
                return True
            return False
        else:
            try:
                cell = self.sheet.find(str(item_id))
                if cell:
                    # status(6), scheduled_date(8)
                    self.sheet.update_cell(cell.row, 6, "scheduled")
                    self.sheet.update_cell(cell.row, 8, str(scheduled_date))
                    return True
                return False
            except Exception as e:
                st.error(f"確定エラー: {e}")
                return False

    def delete_proposal(self, item_id):
        """提案の削除 (物理削除)"""
        if self.use_mock:
            df = st.session_state.mock_db
            idx = df[df['id'] == item_id].index
            if not idx.empty:
                st.session_state.mock_db = df.drop(idx).reset_index(drop=True)
                return True
            return False
        else:
            try:
                cell = self.sheet.find(str(item_id))
                if cell:
                    self.sheet.delete_rows(cell.row)
                    return True
                return False
            except Exception as e:
                st.error(f"削除エラー: {e}")
                return False

    def fetch_categories(self):
        """カテゴリ一覧の取得"""
        if self.use_mock:
            return st.session_state.get("mock_categories", ["旅行", "グルメ", "家", "日常"])
        
        try:
            creds_dict = dict(st.secrets["gcp_service_account"])
            env = st.secrets.get("env", {}).get("current", "dev")
            url_key = f"spreadsheet_url_{env}"
            if "google_sheets" not in st.secrets or url_key not in st.secrets["google_sheets"]:
                 return ["旅行", "グルメ", "家", "日常"]
            
            url = st.secrets["google_sheets"][url_key]
            
            raw_rows = _get_categories_from_sheet(creds_dict, url)
            
            if raw_rows is None or len(raw_rows) <= 1:
                return ["旅行", "グルメ", "家", "日常"]
            
            # ヘッダー(1行目)を除外して重複排除
            categories = []
            seen = set()
            for r in raw_rows[1:]:
                r = r.strip()
                if r and r not in seen:
                    categories.append(r)
                    seen.add(r)
            
            return categories if categories else ["旅行", "グルメ", "家", "日常"]
            
        except Exception:
            return ["旅行", "グルメ", "家", "日常"]

    def add_category(self, category_name):
        """カテゴリの追加"""
        category_name = category_name.strip()
        if not category_name:
            return False, "カテゴリ名が空です"
        
        current_cats = self.fetch_categories()
        if category_name in current_cats:
            return False, "既に存在するカテゴリです"
            
        if self.use_mock:
            if "mock_categories" not in st.session_state:
                st.session_state.mock_categories = ["旅行", "グルメ", "家", "日常"]
            st.session_state.mock_categories.append(category_name)
            return True, "カテゴリを追加しました"
            
        try:
            creds_dict = dict(st.secrets["gcp_service_account"])
            env = st.secrets.get("env", {}).get("current", "dev")
            url_key = f"spreadsheet_url_{env}"
            url = st.secrets["google_sheets"][url_key]
            
            gc = get_gspread_client(creds_dict)
            wb = gc.open_by_url(url)
            try:
                ws = wb.worksheet("categories")
            except:
                # シートがなければ作成（念のため）
                ws = wb.add_worksheet(title="categories", rows=100, cols=2)
                ws.append_row(["category_name"])
            
            ws.append_row([category_name])
            
            # キャッシュクリア
            _get_categories_from_sheet.clear()
            
            return True, "カテゴリを追加しました"
        except Exception as e:
            return False, f"追加エラー: {e}"

    def update_category(self, old_name, new_name):
        """カテゴリ名の変更（関連する提案データも一括更新）"""
        new_name = new_name.strip()
        if not new_name:
            return False, "新しいカテゴリ名が空です"
        
        current_cats = self.fetch_categories()
        if new_name in current_cats:
            return False, "そのカテゴリ名は既に存在します"

        if self.use_mock:
            # カテゴリリストの更新
            if "mock_categories" in st.session_state:
                st.session_state.mock_categories = [new_name if c == old_name else c for c in st.session_state.mock_categories]
            
            # データの一括置換 (mock_db)
            df = st.session_state.mock_db
            count = df[df['category'] == old_name].shape[0]
            df.loc[df['category'] == old_name, 'category'] = new_name
            st.session_state.mock_db = df
            
            return True, f"カテゴリ名を変更しました（影響: {count}件）"
        
        try:
            creds_dict = dict(st.secrets["gcp_service_account"])
            env = st.secrets.get("env", {}).get("current", "dev")
            url_key = f"spreadsheet_url_{env}"
            url = st.secrets["google_sheets"][url_key]
            
            gc = get_gspread_client(creds_dict)
            wb = gc.open_by_url(url)
            
            # 1. Categoriesシートの更新
            ws_cat = wb.worksheet("categories")
            cell = ws_cat.find(old_name)
            if not cell:
                return False, "変更対象のカテゴリが見つかりません"
            
            ws_cat.update_cell(cell.row, cell.col, new_name)
            
            # 2. 提案データの更新 (Sheet1)
            # categoryは4列目と仮定
            cells = self.sheet.findall(old_name)
            # 4列目(D列)のものだけをフィルタリング
            target_cells = [c for c in cells if c.col == 4]
            count = len(target_cells)
            
            if count > 0:
                for c in target_cells:
                    c.value = new_name
                self.sheet.update_cells(target_cells)
            
            # キャッシュクリア
            _get_categories_from_sheet.clear()
            
            return True, f"カテゴリ名を変更しました（関連データ {count}件も同時に更新）"
        except Exception as e:
            return False, f"更新エラー: {e}"

    def update_proposal(self, item_id, updates):
        """提案内容の更新"""
        # updates = {"title": "...", "category": "...", "proposed_date": "...", "scheduled_date": "..."}
        if self.use_mock:
            df = st.session_state.mock_db
            idx = df[df['id'] == item_id].index
            if not idx.empty:
                for col, val in updates.items():
                    if col in df.columns:
                        st.session_state.mock_db.at[idx[0], col] = val
                return True
            return False
        
        try:
            cell = self.sheet.find(str(item_id))
            if not cell:
                return False
            
            # カラム名と列番号のマッピング
            # id(1), user(2), title(3), category(4), proposed_date(5), status(6), created_at(7), scheduled_date(8)
            col_map = {
                "title": 3,
                "category": 4,
                "proposed_date": 5,
                "status": 6,
                "scheduled_date": 8
            }
            
            # バッチ更新用にセルオブジェクトを作成したいが、個別にupdate_cellの方が安全確実か
            # gspreadのupdate_cellは(row, col, value)
            for col_name, val in updates.items():
                if col_name in col_map:
                    self.sheet.update_cell(cell.row, col_map[col_name], str(val))
            
            return True
        except Exception as e:
            st.error(f"更新エラー: {e}")
            return False
