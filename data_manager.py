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

# キャッシュされた接続関数
@st.cache_resource
def get_gspread_client(creds_dict):
    """
    gspreadクライアントをキャッシュして返す関数
    """
    return gspread.service_account_from_dict(creds_dict)

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
                return True
            except Exception as e:
                st.error(f"追加エラー: {e}")
                return False

    def approve_proposal(self, item_id):
        """提案承認 (Status: pending -> approved)"""
        if self.use_mock:
            df = st.session_state.mock_db
            idx = df[df['id'] == item_id].index
            if not idx.empty:
                st.session_state.mock_db.at[idx[0], 'status'] = 'approved'
                return True
            return False
        else:
            try:
                cell = self.sheet.find(str(item_id))
                if cell:
                    # statusカラムは6番目 (F列) と仮定
                    # ヘッダー: id(1), user(2), title(3), category(4), proposed_date(5), status(6), created_at(7), scheduled_date(8)
                    self.sheet.update_cell(cell.row, 6, "approved")
                    return True
                return False
            except Exception as e:
                st.error(f"承認エラー: {e}")
                return False

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
