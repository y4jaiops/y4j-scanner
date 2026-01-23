import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build # <--- NEW: Import Drive API

# We need full Drive scope for this to work
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def _get_creds():
    """Helper to get credentials object"""
    if "gcp_service_account" not in st.secrets:
        st.error("Google Cloud Secrets missing in .streamlit/secrets.toml")
        return None
    creds_dict = dict(st.secrets["gcp_service_account"])
    return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

def _get_gspread_client():
    creds = _get_creds()
    if not creds: return None
    return gspread.authorize(creds)

def create_sheet_via_drive_api(filename, folder_id):
    """
    Creates a sheet DIRECTLY inside the target folder using the Drive API.
    This bypasses the Bot's storage quota limits.
    """
    try:
        creds = _get_creds()
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': filename,
            'parents': [folder_id], # Create directly in target folder
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }

        file = service.files().create(body=file_metadata, fields='id').execute()
        return file.get('id')
    except Exception as e:
        st.error(f"Drive API Create Error: {e}")
        return None

def get_or_create_spreadsheet(filename, folder_id=None):
    """
    Tries to open a sheet by name. If not found, creates it.
    """
    client = _get_gspread_client()
    if not client: return None

    try:
        # 1. Try to open existing sheet
        sh = client.open(filename)
        return sh.url
    except gspread.SpreadsheetNotFound:
        # 2. Not found? Create it
        try:
            if folder_id:
                # --- THE FIX: Use Drive API to create directly in folder ---
                # This prevents "Quota Exceeded" errors on the Bot's account
                new_sheet_id = create_sheet_via_drive_api(filename, folder_id)
                if new_sheet_id:
                    sh = client.open_by_key(new_sheet_id)
                    return sh.url
                else:
                    return None
            else:
                # Fallback to default (might fail if quota full)
                sh = client.create(filename)
                return sh.url
        except Exception as e:
            st.error(f"Error creating sheet: {e}")
            return None

def append_batch_to_sheet(sheet_url, list_of_dicts):
    """
    Appends multiple rows at once (Batch).
    """
    if not list_of_dicts: return True
    try:
        client = _get_gspread_client()
        if not client: return False

        sheet = client.open_by_url(sheet_url).sheet1
        
        # Handle Headers
        existing_headers = sheet.row_values(1)
        if not existing_headers:
            headers = list(list_of_dicts[0].keys())
            sheet.append_row(headers)
        else:
            headers = existing_headers

        # Align data
        rows_to_add = []
        for data in list_of_dicts:
            row = [data.get(h, "") for h in headers]
            rows_to_add.append(row)
        
        sheet.append_rows(rows_to_add)
        return True
    except Exception as e:
        st.error(f"Google Sheet Batch Error: {e}")
        return False
