import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def _get_admin_creds():
    """
    Returns credentials authenticated via the Refresh Token (Admin User).
    This accesses the 2TB Drive, not the Service Account's limited drive.
    """
    if "google_auth" not in st.secrets:
        st.error("Missing [google_auth] in secrets.toml")
        return None

    auth_secrets = st.secrets["google_auth"]
    
    # Create credentials object using the Refresh Token
    creds = Credentials(
        token=None, # Let it fetch a new access token
        refresh_token=auth_secrets["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=auth_secrets["client_id"],
        client_secret=auth_secrets["client_secret"]
    )
    
    # Refresh the token if needed
    if not creds.valid:
        creds.refresh(Request())
        
    return creds

def _get_gspread_client():
    creds = _get_admin_creds()
    if not creds: return None
    return gspread.authorize(creds)

def get_or_create_spreadsheet(filename, folder_id=None):
    """
    Creates/Opens a sheet acting as the ADMIN USER (You).
    """
    client = _get_gspread_client()
    if not client: return None

    try:
        # 1. Try to open existing
        sh = client.open(filename)
        return sh.url
    except gspread.SpreadsheetNotFound:
        # 2. Not found? Create it
        try:
            creds = _get_admin_creds()
            service = build('drive', 'v3', credentials=creds)
            
            file_metadata = {
                'name': filename,
                'mimeType': 'application/vnd.google-apps.spreadsheet'
            }
            
            # If folder is specified, put it there
            if folder_id:
                file_metadata['parents'] = [folder_id]

            file = service.files().create(body=file_metadata, fields='id').execute()
            
            # Open the newly created sheet to return URL
            new_sheet_id = file.get('id')
            sh = client.open_by_key(new_sheet_id)
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
        st.error(f"Batch Save Error: {e}")
        return False
