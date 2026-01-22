import streamlit as st
import pandas as pd
import time
from logic_gemini import parse_document_dynamic
from logic_sheets import append_batch_to_sheet
from logic_drive import get_file_from_link

st.set_page_config(page_title="Y4J YouthScan App", page_icon="🇮🇳", layout="wide")
st.title("🇮🇳 Youth4Jobs Smart Scanner")

# --- SESSION STATE SETUP ---
if 'drive_data' not in st.session_state:
    st.session_state['drive_data'] = None
if 'drive_mime' not in st.session_state:
    st.session_state['drive_mime'] = None

def clear_drive_data():
    """Callback to clear drive data if user uses Camera or Upload tabs"""
    st.session_state['drive_data'] = None
    st.session_state['drive_mime'] = None

# --- SIDEBAR ---
with st.sidebar:
    st.header("Configuration")
    
    sheet_url = st.text_input("Paste Google Sheet URL here:")
    if sheet_url and "xlsx" in sheet_url:
        st.error("⚠️ You pasted a link to an Excel file (.xlsx). Please convert it to a Google Sheet first (File > Save as Google Sheets).")

    default_cols = "First Name, Last Name, ID Type, ID Number, Email, PhoneNumber, DateOfBirth, Gender, DisabilityType, Qualification, State"
    cols_input = st.text_area("Columns to Extract", value=default_cols, height=150)
    target_columns = [x.strip() for x in cols_input.split(",") if x.strip()]
    
    if "gcp_service_account" in st.secrets:
        bot_email = st.secrets["gcp_service_account"]["client_email"]
        st.info(f"🤖 **Bot Email:**\n`{bot_email}`\n\n(Share Drive files with this email!)")

# --- MAIN AREA ---
tab1, tab2, tab3 = st.tabs(["📸 Camera", "📂 Upload File", "🔗 Google Drive Link"])

# Variables to hold the current "active" file
active_image_data = None
active_mime_type = "image/jpeg"

# 1. Camera
with tab1:
    # on_change ensures that if I take a new photo, I stop looking at the Drive file
    cam = st.camera_input("Take a photo", on_change=clear_drive_data, key="cam_widget")

# 2. Upload
with tab2:
    # on_change ensures that if I upload a new file, I stop looking at the Drive file
    up = st.file_uploader("Upload Image/PDF", type=["jpg", "png", "jpeg", "pdf"], 
                          on_change=clear_drive_data, key="up_widget")

# 3. Google Drive Link
with tab3:
    st.markdown("1. Share the file with the **Bot Email** (see sidebar).")
    st.markdown("2. Paste the link below.")
    drive_link = st.text_input("Google Drive Link")
    if drive_link:
        if st.button("📥 Fetch from Drive"):
            with st.spinner("Downloading from Drive..."):
                file_bytes, detected_mime, error = get_file_from_link(drive_link)
                if error:
                    st.error(error)
                else:
                    # STORE IN SESSION STATE so it persists when buttons are clicked later
                    st.session_state['drive_data'] = file_bytes
                    st.session_state['drive_mime'] = detected_mime
                    st.success(f"Loaded: {detected_mime}")

# --- DETERMINE SOURCE ---
# Priority: 1. Drive Data (if active) -> 2. Upload -> 3. Camera
if st.session_state['drive_data'] is not None:
    active_image_data = st.session_state['drive_data']
    active_mime_type = st.session_state['drive_mime']
elif up:
    active_image_data = up.getvalue()
    active_mime_type = up.type
elif cam:
    active_image_data = cam.getvalue()
    active_mime_type = "image/jpeg"


# --- PROCESSING ---
if active_image_data:
    st.divider()
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown(f"**Loaded Document ({active_mime_type})**")
        
        # Helper to show source clearly
        source_label = "Source: Google Drive" if st.session_state['drive_data'] else "Source: Local Upload/Camera"
        st.caption(source_label)

        if "image" in active_mime_type:
            st.image(active_image_data, use_column_width=True)
        else:
            st.info("📄 PDF Document Loaded")
        
        if st.button("🚀 Analyze with Gemini", type="primary"):
            if not sheet_url:
                st.warning("Please enter a Google Sheet URL first.")
            else:
                with st.spinner("Gemini is analyzing..."):
                    result = parse_document_dynamic(active_image_data, target_columns, active_mime_type)
                    
                    if result and isinstance(result, list) and "error" in result[0]:
                        st.error(f"AI Error: {result[0]['error']}")
                    else:
                        st.session_state['result_df'] = pd.DataFrame(result)

    with col2:
        if 'result_df' in st.session_state:
            st.subheader("Verify Data")
            edited_df = st.data_editor(st.session_state['result_df'], num_rows="dynamic", use_container_width=True)
            
            if st.button("💾 Save ALL to Google Sheet"):
                if not sheet_url:
                     st.error("Please provide a Google Sheet URL in the sidebar.")
                else:
                    with st.spinner("Saving all rows at once..."):
                        # BATCH LOGIC
                        data_to_save = edited_df.to_dict('records')
                        success = append_batch_to_sheet(sheet_url, data_to_save)
                        
                        if success:
                            st.success(f"✅ Successfully saved {len(data_to_save)} candidates!")
                            st.balloons()
                        else:
                            st.error("Failed to save data. Check the logs.")
