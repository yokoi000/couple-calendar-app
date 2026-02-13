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

class DataManager:
    """
    データの取得・保存を行うクラス。
    Google Sheetsが設定されていない場合は、自動的にセッションステートを使用したモックモード（Mock Mode）で動作します。
    """
    def __init__(self):
        self.use_mock = True
        self.sheet = None
        self._initialize_connection()

    def _initialize_connection(self):
        """
        secrets.tomlの設定を使ってGoogle Sheetsへの接続を試みます。
        接続できない場合はモックモードを有効にします。
        """
        # 簡易チェック: secretsにプロジェクトIDが設定されているか
        has_secrets = "gcp_service_account" in st.secrets and "your-project-id" not in st.secrets["gcp_service_account"]["project_id"]
        
        if has_secrets and HAS_GSPREAD:
            try:
                creds_dict = dict(st.secrets["gcp_service_account"])
                gc = gspread.service_account_from_dict(creds_dict)
                sheet_name = st.secrets["google_sheets"]["sheet_name"]
                self.sheet = gc.open(sheet_name).sheet1
                self.use_mock = False
                # 接続成功時はログに出すのみ（画面には出さない）
                print("Google Sheetsに接続しました。")
            except Exception as e:
                print(f"Google Sheetsへの接続に失敗しました: {e}。モックモードで動作します。")
                self.use_mock = True
        else:
            print("Google Sheets設定が見つからないため、モックモードで動作します。")
            self.use_mock = True

        # モック（デモ）用データの初期化
        if self.use_mock:
            if "mock_db" not in st.session_state:
                # データフレームの初期化
                st.session_state.mock_db = pd.DataFrame(columns=[
                    "id", "user", "title", "category", "status", "proposed_date", "scheduled_date", "timestamp"
                ])
                # デモデータの追加
                dummy_data = [
                    {"id": "1", "user": "あなた", "title": "北海道旅行に行きたい", "category": "旅行", "status": "pending", "proposed_date": "2024-05-01", "scheduled_date": "", "timestamp": datetime.datetime.now().isoformat()},
                    {"id": "2", "user": "彼女", "title": "新しいソファを見る", "category": "家", "status": "approved", "proposed_date": "2024-02-20", "scheduled_date": "2024-02-25", "timestamp": datetime.datetime.now().isoformat()},
                    {"id": "3", "user": "彼女", "title": "美味しいイタリアン", "category": "グルメ", "status": "pending", "proposed_date": "", "scheduled_date": "", "timestamp": datetime.datetime.now().isoformat()},
                ]
                st.session_state.mock_db = pd.concat([st.session_state.mock_db, pd.DataFrame(dummy_data)], ignore_index=True)

    def fetch_data(self):
        """
        データをPandas DataFrameとして取得します。
        """
        if self.use_mock:
            return st.session_state.mock_db
        else:
            try:
                data = self.sheet.get_all_records()
                df = pd.DataFrame(data)
                expected_cols = ["id", "user", "title", "category", "status", "proposed_date", "scheduled_date", "timestamp"]
                # カラムが不足している場合は空文字で埋める
                for col in expected_cols:
                    if col not in df.columns:
                        df[col] = ""
                return df
            except Exception as e:
                st.error(f"データの取得中にエラーが発生しました: {e}")
                return pd.DataFrame()

    def add_proposal(self, user, title, category, proposed_date=""):
        """
        新しい提案を追加します。
        """
        new_row = {
            "id": str(datetime.datetime.now().timestamp()), # 簡易的なID生成
            "user": user,
            "title": title,
            "category": category,
            "status": "pending",
            "proposed_date": str(proposed_date) if proposed_date else "",
            "scheduled_date": "",
            "timestamp": datetime.datetime.now().isoformat()
        }

        if self.use_mock:
            st.session_state.mock_db = pd.concat([st.session_state.mock_db, pd.DataFrame([new_row])], ignore_index=True)
            return True
        else:
            try:
                # 辞書の値をリストに変換して追加
                values = list(new_row.values())
                self.sheet.append_row(values)
                return True
            except Exception as e:
                st.error(f"提案の追加に失敗しました: {e}")
                return False

    def approve_proposal(self, item_id, scheduled_date):
        """
        提案を承認（ステータスをapprovedに更新）し、日付を確定させます。
        """
        if self.use_mock:
            df = st.session_state.mock_db
            idx = df[df['id'] == item_id].index
            if not idx.empty:
                st.session_state.mock_db.at[idx[0], 'status'] = 'approved'
                st.session_state.mock_db.at[idx[0], 'scheduled_date'] = str(scheduled_date)
                return True
            return False
        else:
            try:
                # IDに対応するセルを検索
                cell = self.sheet.find(str(item_id))
                if cell:
                    row = cell.row
                    # カラム位置は固定と仮定（MVPのため）: Status(5), ScheduledDate(7)
                    self.sheet.update_cell(row, 5, "approved")
                    self.sheet.update_cell(row, 7, str(scheduled_date))
                    return True
                return False
            except Exception as e:
                st.error(f"承認処理に失敗しました: {e}")
                return False
