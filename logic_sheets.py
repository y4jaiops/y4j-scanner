import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def _get_gspread_client():
    if "gcp_service_account" not in st.secrets:
        st.error("Google Cloud Secrets missing in .streamlit/secrets.toml")
        return None
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def get_or_create_spreadsheet(filename, folder_id=None):
    """
    Tries to open a sheet by name. If not found, creates it.
    If folder_id is provided, creates the new sheet INSIDE that folder.
    Returns: The spreadsheet URL (str)
    """
    client = _get_gspread_client()
    if not client: return None

    try:
        # 1. Try to open existing sheet by name
        sh = client.open(filename)
        return sh.url
    except gspread.SpreadsheetNotFound:
        # 2. Not found? Create a new one
        try:
            # Create in specific folder if provided, else root
            # Note: folder_id arg requires gspread >= 5.1.0
            sh = client.create(filename, folder_id=folder_id)
            
            # Share with the user's email so they can see it!
            # (Optional: You can add this if you want the bot to auto-share with you)
            # sh.share('your_personal_email@gmail.com', perm_type='user', role='writer')
            
            return sh.url
        except Exception as e:
            st.error(f"Error creating sheet: {e}")
            return None

def append_batch_to_sheet(sheet_url, list_of_dicts):
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
