import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import re

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets missing.")
        return None
    
    # 1. Load the secrets
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # 2. THE FIX: Handle the private key formatting manually
    # The error happens because the key has literal "\n" characters
    if "private_key" in creds_dict:
        raw_key = creds_dict["private_key"]
        # Replace escaped newlines with actual newlines
        fixed_key = raw_key.replace("\\n", "\n")
        creds_dict["private_key"] = fixed_key
    
    try:
        # 3. Create Credentials with the fixed key
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Authentication Error: {str(e)}")
        return None

def get_file_from_link(drive_link):
    # A. Extract File ID
    file_id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", drive_link)
    if not file_id_match:
        file_id_match = re.search(r"id=([a-zA-Z0-9-_]+)", drive_link)
    
    if not file_id_match:
        return None, None, "Invalid Google Drive Link"
        
    file_id = file_id_match.group(1)
    
    # B. Connect
    service = get_drive_service()
    if not service:
        return None, None, "Auth Failed"

    try:
        # C. Get Metadata
        meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
        mime_type = meta.get('mimeType')

        # D. Download
        # Using .execute() directly returns bytes for get_media
        request = service.files().get_media(fileId=file_id)
        file_content = request.execute()
        
        return file_content, mime_type, None

    except Exception as e:
        return None, None, f"Drive Error: {str(e)}"
