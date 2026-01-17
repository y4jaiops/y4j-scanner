import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def append_to_sheet(sheet_url, data_dict):
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("Google Cloud Secrets missing in .streamlit/secrets.toml")
            return False

        # Authenticate using the modern google-auth library
        # This handles the private_key "\n" formatting automatically
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        
        # Open Sheet
        sheet = client.open_by_url(sheet_url).sheet1
        
        # If sheet is empty, add headers first
        if not sheet.row_values(1):
            sheet.append_row(list(data_dict.keys()))
            
        # Ensure we write data in the same order as the headers
        headers = sheet.row_values(1)
        row_to_add = [data_dict.get(h, "") for h in headers]
        
        sheet.append_row(row_to_add)
        return True
    except Exception as e:
        st.error(f"Google Sheet Error: {e}")
        return False
