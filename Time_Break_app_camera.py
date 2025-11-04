import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timezone, timedelta
import os
import numpy as np
import math
import pathlib
from streamlit_qrcode_scanner import qrcode_scanner

# -----------------------------------------------------------------
# 💥 [GSHEETS] ลบการอ้างอิงไฟล์ CSV ทั้งหมด
# LOGS_DIR = os.path.join(os.path.expanduser('~'), 'Desktop', 'TimeLogs')
# DATA_FILE = os.path.join(LOGS_DIR, "time_logs.csv")
# USER_DATA_FILE = os.path.join(LOGS_DIR, "user_data.csv")
# -----------------------------------------------------------------

# 💥 [GSHEETS] ชื่อคอลัมน์ (ยังคงใช้เหมือนเดิม)
CSV_COLUMNS = ['Employee_ID', 'Date', 'Start_Time', 'End_Time', 'Activity_Type', 'Duration_Minutes']
USERS_COLUMNS = ['Employee_ID'] # 💥 สำหรับแท็บ Users

# --- CSS (เหมือนเดิม) ---
CUSTOM_CSS = """
<style>
div.block-container { padding-top: 1rem; padding-bottom: 0rem; }
div.stButton > button[kind="secondaryFormSubmit"] { padding: 1px 5px !important; font-size: 10px !important; height: 22px !important; line-height: 1 !important; }
.time-display { font-size: 1.1em; font-weight: bold; margin-top: -10px; margin-bottom: -10px; }
.stForm { padding: 10px; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 5px; }
div.stButton button[data-testid="baseButton-primary"] { background-color: #00FFFF !important; border-color: #00FFFF !important; color: black !important; }
div.stButton button[data-testid="baseButton-primary"]:hover { background-color: #33FFFF !important; border-color: #33FFFF !important; }
div.stButton button[data-testid="baseButton-secondary"] { color: #00FFFF !important; border-color: #00FFFF !important; }
</style>
"""


# -----------------------------------------------------------------
# 💥 [GSHEETS] 1. ฟังก์ชันจัดการข้อมูล (เขียนใหม่ทั้งหมด)
# -----------------------------------------------------------------

# 💥 [GSHEETS] สร้างการเชื่อมต่อ
# Streamlit จะดึงข้อมูลจาก 'gsheets' ใน Secrets (ขั้นตอนที่ 4)
@st.cache_resource
def get_gsheets_connection():
    try:
        return st.connection("gsheets") # ✅ แก้ให้เป็นแบบนี้ (ง่ายกว่าเดิม)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ Google Sheets: {e}")
        st.error("กรุณาตรวจสอบว่าตั้งค่า [gsheets] ใน st.secrets ถูกต้อง (ขั้นตอนที่ 4)")
        st.stop()

@st.cache_data(ttl=10) # 💥 Cache 10 วินาที เพื่อให้ข้อมูลค่อนข้างสดใหม่
def load_data(conn):
    """โหลดข้อมูลจาก Google Sheets (แท็บ 'Logs')"""
    try:
        # ใช้ usecols เพื่ออ่านเฉพาะ 6 คอลัมน์แรก
        df = conn.read(worksheet="Logs", usecols=list(range(len(CSV_COLUMNS))), header=0)
        
        # กรองแถวที่ว่างเปล่า (กรณีที่อาจมีแถวว่างใน Sheet)
        df = df.dropna(subset=[CSV_COLUMNS[0]], how='all')

        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date']).dt.date.astype(str)
            df['Start_Time'] = df['Start_Time'].astype(str)
            df['End_Time'] = df['End_Time'].astype(str).replace('nan', np.nan).replace('', np.nan)
            df['Duration_Minutes'] = pd.to_numeric(df['Duration_Minutes'], errors='coerce')
        else:
            df = pd.DataFrame(columns=CSV_COLUMNS)

        # 💥 [GSHEETS] เพิ่ม index ของแถวใน GSheet จริงๆ (สำคัญมากสำหรับ Update/Delete)
        # +1 เพราะ gspread เริ่มที่แถว 1, +1 เพราะข้ามแถว Header
        df['gsheet_row_index'] = df.index + 2
        
        return df.reindex(columns=CSV_COLUMNS + ['gsheet_row_index'])

    except Exception as e:
        # st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล Logs: {e}")
        # อาจเกิด error ถ้าชีตว่างเปล่าครั้งแรก
        return pd.DataFrame(columns=CSV_COLUMNS + ['gsheet_row_index'])

# 💥 [GSHEETS] ลบฟังก์ชัน initialize_data_file() และ save_data(df)
# (เราจะใช้ .append_rows() และ .update() แทน)


@st.cache_data(ttl=60) # 💥 Cache 1 นาที สำหรับ User ID
def load_user_data(conn):
    """โหลดข้อมูล ID พนักงานที่ไม่ซ้ำจากแท็บ 'Users'"""
    try:
        df = conn.read(worksheet="Users", usecols=[0], header=0)
        df = df.dropna(how='all')
        if 'Employee_ID' not in df.columns:
             return []
        return df['Employee_ID'].dropna().astype(str).unique().tolist()
    except Exception as e:
        # st.error(f"เกิดข้อผิดพลาดในการโหลด User ID: {e}")
        # อาจเกิด error ถ้าชีตว่างเปล่าครั้งแรก
        return []

def save_unique_user_id(conn, employee_id):
    """บันทึก ID พนักงานใหม่ที่ไม่ซ้ำลงในแท็บ 'Users'"""
    employee_id = str(employee_id)
    if not employee_id:
        return

    # 💥 โหลดแบบไม่ใช้ Cache เพื่อตรวจสอบค่าล่าสุด
    try:
        df_users = conn.read(worksheet="Users", usecols=[0], header=0)
        existing_ids = df_users['Employee_ID'].dropna().astype(str).unique().tolist()
    except Exception:
        existing_ids = []
    
    if employee_id not in existing_ids:
        try:
            # 💥 สร้าง DataFrame ใหม่สำหรับ append
            df_new_user = pd.DataFrame([[employee_id]], columns=USERS_COLUMNS)
            # 💥 append_rows จะเพิ่มแถวต่อท้ายชีต (ไม่ต้องส่ง Header)
            conn.append_rows(worksheet="Users", data=df_new_user, header=False)
            st.cache_data.clear() # 💥 ล้าง Cache ทั้งหมดเพื่อให้โหลดใหม่
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการบันทึก User ID ลง Google Sheets: {e}")


# 💥 ฟังก์ชัน calculate_duration (เหมือนเดิม)
def calculate_duration(start_time_str, end_time_str):
    try:
        if pd.isnull(start_time_str) or pd.isnull(end_time_str) or str(start_time_str).lower() == 'nan' or str(end_time_str).lower() == 'nan':
            return np.nan
        date_time_format = '%H:%M:%S'
        base_date = datetime(2000, 1, 1)
        t_start_time = datetime.strptime(str(start_time_str), date_time_format).time()
        t_end_time = datetime.strptime(str(end_time_str), date_time_format).time()
        t_start = datetime.combine(base_date, t_start_time)
        t_end = datetime.combine(base_date, t_end_time)
        if t_end < t_start:
            t_end += pd.Timedelta(days=1)
        duration_minutes = (t_end - t_start).total_seconds() / 60
        return max(0, duration_minutes)
    except (ValueError, TypeError, AttributeError):
        return np.nan

# 💥 [GSHEETS] ฟังก์ชัน Clock Out (แก้ไขใหม่)
def clock_out_latest_activity(conn, employee_id, date_str, end_time_str):
    """ค้นหาและ Clock Out กิจกรรมล่าสุดที่ยังเปิดอยู่ (ใน Google Sheets)"""
    df = load_data(conn) # 💥 โหลดข้อมูลล่าสุด
    
    condition = (df['Employee_ID'] == employee_id) & \
                (df['Date'] == date_str) & \
                (df['End_Time'].isna() | (df['End_Time'] == 'nan') | (df['End_Time'] == ''))
                
    ongoing_activities = df[condition]

    if not ongoing_activities.empty:
        # 💥 หาแถว GSheet index ที่จะอัปเดต
        row_to_update_index = ongoing_activities['gsheet_row_index'].max()
        
        # 💥 หาค่า Start_Time จาก DataFrame
        start_time = ongoing_activities.loc[ongoing_activities['gsheet_row_index'] == row_to_update_index, 'Start_Time'].values[0]
        
        duration = calculate_duration(start_time, end_time_str)
        
        try:
            # 💥 [GSHEETS] อัปเดตข้อมูล 2 เซลล์ ในแถวที่ถูกต้อง
            # เราใช้ client ของ gspread เพื่อความยืดหยุ่นในการอัปเดตแบบ Range
            # "D" คือ End_Time, "F" คือ Duration_Minutes (คอลัมน์ที่ 4 และ 6)
            ws = conn.client.worksheet("Logs")
            # 💥 สร้าง list ของค่าที่จะอัปเดต
            values_to_update = [
                [end_time_str, np.nan, duration] # [End_Time, (ข้าม Activity_Type), Duration_Minutes]
            ]
            
            # 💥 อัปเดตแถว โดยเริ่มที่คอลัมน์ D (คอลัมน์ที่ 4)
            ws.update(f'D{row_to_update_index}:F{row_to_update_index}', values_to_update, value_input_option='USER_ENTERED')
            
            st.cache_data.clear() # 💥 ล้าง Cache
            return True
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการอัปเดต Google Sheets (Clock Out): {e}")
            return False
    return False 

# 💥 [GSHEETS] ฟังก์ชันเริ่มพักเบรคใหม่ (แก้ไขใหม่)
def log_activity_start(conn, employee_id, date_str, start_time_str, activity_type):
    """บันทึกการเริ่มพักเบรคใหม่ และ Clock Out กิจกรรมเดิม (ถ้ามี)"""
    try:
        # 1. Clock out อันเก่าก่อน (Logic เดิม)
        clock_out_latest_activity(conn, employee_id, date_str, start_time_str) 
        
        # 2. 💥 สร้าง DataFrame แถวใหม่
        new_row_df = pd.DataFrame([{
            'Employee_ID': employee_id,
            'Date': date_str,
            'Start_Time': start_time_str,
            'End_Time': np.nan, # ใช้ np.nan จะดีกว่า
            'Activity_Type': activity_type,
            'Duration_Minutes': np.nan
        }])
        
        # 3. 💥 Append แถวใหม่ลง Google Sheets
        conn.append_rows(worksheet="Logs", data=new_row_df, header=False)
        
        # 4. บันทึก ID ผู้ใช้ (Logic เดิม)
        save_unique_user_id(conn, employee_id)
        
        st.cache_data.clear() # 💥 ล้าง Cache
        return True
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเริ่มพักเบรค {activity_type} (Google Sheets): {e}")
        return False


def delete_log_entry(conn, gsheet_row_index):
    """ลบ Log ตาม GSheet Row Index"""
    try:
        # 💥 [GSHEETS] ใช้ client ของ gspread เพื่อลบแถว
        ws = conn.client.worksheet("Logs")
        ws.delete_rows(int(gsheet_row_index)) # 💥 gspread ใช้ 1-indexed row number
        st.cache_data.clear() # 💥 ล้าง Cache
        st.success(f"ลบแถวที่ {gsheet_row_index} เรียบร้อยแล้ว")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการลบแถว {gsheet_row_index}: {e}")


# --- 2. ฟังก์ชันคำนวณและแสดงผล (เหมือนเดิม) ---

def format_time_display(time_str):
    if pd.isnull(time_str) or str(time_str).lower() == 'nan':
        return "N/A"
    try:
        return datetime.strptime(str(time_str), '%H:%M:%S').strftime('%H:%M')
    except (ValueError, TypeError):
        return str(time_str).split('.')[0] 

def format_duration(minutes):
    if pd.isnull(minutes) or (isinstance(minutes, float) and math.isnan(minutes)):
        return "N/A"
    try:
        minutes = int(float(minutes)) 
    except (ValueError, TypeError):
        return "N/A" 
    if minutes < 0:
        return "00:00"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"


# 💥 [GSHEETS] ลบฟังก์ชัน get_csv_content_with_bom()


# -----------------------------------------------------------------
# 💥 [GSHEETS] ฟังก์ชัน Callback (ปรับปรุงเล็กน้อย)
# -----------------------------------------------------------------
def submit_activity(activity_type):
    # 💥 [GSHEETS] รับ conn จาก session_state
    conn = st.session_state.get("gsheets_conn")
    if not conn:
        st.error("ไม่พบการเชื่อมต่อ Google Sheets")
        return

    emp_id = st.session_state.get("current_emp_id", "")
    if not emp_id:
        st.session_state.last_message = ("warning", "กรุณาสแกนหรือกรอก Employee ID ก่อนทำกิจกรรม")
        return 

    THAILAND_TZ = timezone(timedelta(hours=7))
    now_thailand = datetime.now(THAILAND_TZ)
    current_date_str = now_thailand.date().strftime('%Y-%m-%d')
    current_time_str = now_thailand.time().strftime('%H:%M:%S')

    if activity_type == "End_Activity":
        # 💥 [GSHEETS] ส่ง conn เข้าไปด้วย
        if clock_out_latest_activity(conn, emp_id, current_date_str, current_time_str):
            st.session_state.last_message = ("success", f"✅ สิ้นสุดกิจกรรมล่าสุด สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อยแล้ว!")
            st.session_state["current_emp_id"] = "" 
            st.session_state["manual_emp_id_input_outside_form"] = "" 
            st.session_state["selectbox_chooser"] = "--- เลือก ID (ถ้ามี) ---" 
        else:
            st.session_state.last_message = ("warning", f"⚠️ ไม่พบกิจกรรมที่กำลังดำเนินอยู่สำหรับ ID: **{emp_id}** วันที่ {current_date_str}")
            
    else:
        # (activity_type คือ "Break", "Smoking", "Toilet")
        # 💥 [GSHEETS] ส่ง conn เข้าไปด้วย
        if log_activity_start(conn, emp_id, current_date_str, current_time_str, activity_type):
            success_message = f"✅ เริ่มพักเบรค **{activity_type}** สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อยแล้ว!"
            # (... logic ข้อความ success เหมือนเดิม ...)
            
            st.session_state.last_message = ("success", success_message)
            st.session_state["current_emp_id"] = "" 
            st.session_state["manual_emp_id_input_outside_form"] = "" 
            st.session_state["selectbox_chooser"] = "--- เลือก ID (ถ้ามี) ---"
        else:
            st.session_state.last_message = ("error", f"เกิดข้อผิดพลาดในการเริ่มพักเบรค {activity_type}")
            
    st.rerun() 


# -----------------------------------------------------------------
# 💥 [GSHEETS] ฟังก์ชัน MAIN (ปรับปรุง)
# -----------------------------------------------------------------
def main():
    st.set_page_config(page_title="Time Logger", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Initialize Session State
    if "current_emp_id" not in st.session_state:
        st.session_state["current_emp_id"] = ""
    if "manual_emp_id_input_outside_form" not in st.session_state: 
        st.session_state["manual_emp_id_input_outside_form"] = ""
    if "last_message" not in st.session_state:
        st.session_state.last_message = None
    if "selectbox_chooser" not in st.session_state: 
        st.session_state["selectbox_chooser"] = "--- เลือก ID (ถ้ามี) ---"

    # 💥 [GSHEETS] 3.1 การเริ่มต้นการเชื่อมต่อ
    conn = get_gsheets_connection()
    # 💥 [GSHEETS] เก็บ conn ไว้ใน state เพื่อให้ callback ใช้ได้
    st.session_state["gsheets_conn"] = conn 


    # 💥 [GSHEETS] 3.2 โหลดข้อมูล
    df = load_data(conn) 
    existing_ids = sorted(load_user_data(conn)) # 💥 [GSHEETS] โหลด ID จากชีต


    # -----------------------------------------------------------------
    # --- Layout หลัก ---
    main_col1, main_col2 = st.columns([1, 2])

    with main_col1:
        st.title("ระบบบันทึกเวลา")
        # 💥 [GSHEETS] ลบ path ที่แสดงออก
        # st.markdown(f"**บันทึกข้อมูลที่:** `{LOGS_DIR}`") 
        
        # ... (ส่วนแสดง Message เหมือนเดิม) ...
        if st.session_state.last_message:
            msg_type, msg_content = st.session_state.last_message
            if msg_type == "success": st.success(msg_content)
            elif msg_type == "warning": st.warning(msg_content)
            elif msg_type == "error": st.error(msg_content)
            st.session_state.last_message = None 
        
        #st.subheader("บันทึกกิจกรรม")

        # ... (ส่วน Selectbox, Text Input, Callbacks เหมือนเดิม) ...
        options = ["--- เลือก ID (ถ้ามี) ---"] + existing_ids 
        
        def sync_from_selectbox():
            selected_val = st.session_state.selectbox_chooser
            if selected_val and selected_val != "--- เลือก ID (ถ้ามี) ---":
                st.session_state.manual_emp_id_input_outside_form = selected_val
                st.session_state.current_emp_id = selected_val

        def sync_from_text_input():
            typed_val = st.session_state.manual_emp_id_input_outside_form.strip()
            st.session_state.current_emp_id = typed_val
            if typed_val in existing_ids:
                st.session_state.selectbox_chooser = typed_val
            else:
                st.session_state.selectbox_chooser = "--- เลือก ID (ถ้ามี) ---"

        st.selectbox(
            "หรือเลือก ID ที่มีอยู่:",
            options=options,
            key="selectbox_chooser",
            on_change=sync_from_selectbox,
            help="""เลือก ID จาก
    ที่นี่จะเติมค่าลงในช่อง 'กรอก ID' ด้านล่าง"""
        )

        st.text_input(
            "กรอก ID ด้วยมือ:", 
            key="manual_emp_id_input_outside_form", 
            on_change=sync_from_text_input,
            placeholder="กรอก ID ที่นี่ หรือเลือกจากด้านบน"
        )
        
        emp_id_input = st.session_state.get("current_emp_id", "").strip()
        
        # ... (ส่วน Form และปุ่มกิจกรรม เหมือนเดิม) ...
        with st.form("activity_form", clear_on_submit=False): 
            if emp_id_input:
                st.info(f"ID ที่ใช้บันทึก: **{emp_id_input}**")
            else:
                st.info("กรุณาสแกน, เลือก หรือกรอก Employee ID ก่อนทำกิจกรรม")
            st.write("เลือกกิจกรรม:")
            activity_buttons_col1, activity_buttons_col2, activity_buttons_col3, activity_buttons_col4 = st.columns(4)
            is_disabled = not bool(emp_id_input) 
            
            submitted_Break = activity_buttons_col1.form_submit_button("เริ่มพักเบรค", type="primary", use_container_width=True, disabled=is_disabled,
                                                                    on_click=submit_activity, args=("Break",))
            submitted_smoking = activity_buttons_col2.form_submit_button("สูบบุหรี่", use_container_width=True, disabled=is_disabled,
                                                                       on_click=submit_activity, args=("Smoking",))
            submitted_toilet = activity_buttons_col3.form_submit_button("เข้าห้องน้ำ", use_container_width=True, disabled=is_disabled,
                                                                      on_click=submit_activity, args=("Toilet",))
            submitted_end_activity = activity_buttons_col4.form_submit_button("สิ้นสุดกิจกรรม", type="secondary", use_container_width=True, disabled=is_disabled,
                                                                           on_click=submit_activity, args=("End_Activity",))

        # ... (ส่วน QR Code Scanner เหมือนเดิม) ...
        st.write("---") 
        st.write("หรือ สแกน QR/Barcode:")
        scanned_id = qrcode_scanner(key="qrcode_scanner_key_new")
        
        if scanned_id and scanned_id != st.session_state.get("current_emp_id", ""):
            st.session_state["current_emp_id"] = scanned_id
            st.session_state["manual_emp_id_input_outside_form"] = scanned_id 
            if scanned_id in existing_ids:
                st.session_state["selectbox_chooser"] = scanned_id
            else:
                st.session_state["selectbox_chooser"] = "--- เลือก ID (ถ้ามี) ---"
            st.rerun()


    # -----------------------------------------------------------------
    # ส่วนคอลัมน์ขวา (แสดงข้อมูล)
    # -----------------------------------------------------------------
    with main_col2:
        st.markdown("---")
        st.subheader("ข้อมูลลงเวลา (จาก Google Sheets)")

        # --- ส่วน Filter (เหมือนเดิม) ---
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        filter_date_from = col_filter1.date_input("กรองตามวันที่ (From)", value=datetime.now().date(), key="date_from_key")
        filter_date_to = col_filter2.date_input("กรองตามวันที่ (To)", value=datetime.now().date(), key="date_to_key")
        
        unique_ids = ["All"] + existing_ids # 💥 [GSHEETS] ใช้ existing_ids ที่โหลดไว้
        filter_id = col_filter3.selectbox("กรองตาม Employee ID", options=unique_ids, key="id_filter_key")


        # --- สร้างตารางแสดงผล (ปรับปรุงเล็กน้อย) ---
        if df.empty:
            st.info("ยังไม่มีข้อมูลการลงเวลา")
        else:
            display_df = df.copy()
            # 💥 [GSHEETS] เปลี่ยนมาใช้ 'Date' ที่เป็น string แล้ว ไม่ต้องแปลง Date_Obj
            display_df = display_df.dropna(subset=['Date']) # กรองแถวที่ Date เป็นค่าว่าง
            display_df['Date_Obj'] = pd.to_datetime(display_df['Date']).dt.date

            if filter_date_from and filter_date_to:
                if filter_date_from <= filter_date_to:
                    display_df = display_df[
                        (display_df['Date_Obj'] >= filter_date_from) &
                        (display_df['Date_Obj'] <= filter_date_to)
                    ]
                else:
                    st.error("วันที่ From ต้องไม่เกินวันที่ To กรุณาแก้ไข")
                    st.stop() 

            if filter_id != "All":
                display_df = display_df[display_df['Employee_ID'] == filter_id]

            if display_df.empty:
                st.info("ไม่พบข้อมูลการลงเวลาตามตัวกรองที่เลือก")
            else:
                display_df = display_df.drop(columns=['Date_Obj'], errors='ignore')
                display_df = display_df.sort_values(by=['Date', 'Start_Time'], ascending=[False, False])
                display_df = display_df.reset_index(drop=True) 

                col_ratios = [0.5, 1, 1, 1.2, 1, 1, 1.3]
                cols = st.columns(col_ratios)
                headers = ["ลบ", "Employee ID", "Date", "ประเภทกิจกรรม", "เวลาเริ่ม", "เวลาสิ้นสุด", "**ระยะเวลา**"]
                for col, header in zip(cols, headers):
                    col.markdown(f"**{header}**")
                
                st.markdown('<hr style="margin: 0px 0px 0px 0px;">', unsafe_allow_html=True) 

                for index, row in display_df.iterrows(): 
                    # 💥 [GSHEETS] ใช้ gsheet_row_index สำหรับการลบ
                    gsheet_row_index = row['gsheet_row_index']
                    cols = st.columns(col_ratios)
                    time_style = "class='time-display'"
                    
                    # 💥 [GSHEETS] ส่ง conn และ gsheet_row_index เข้าไป
                    if cols[0].button("❌", key=f"del_{gsheet_row_index}", on_click=delete_log_entry, args=(conn, gsheet_row_index,), help="ลบ Log ลงเวลานี้"):
                         st.rerun()
                         
                    cols[1].write(row['Employee_ID'])
                    cols[2].write(row['Date'])
                    cols[3].write(row['Activity_Type'])
                    cols[4].markdown(f"<p {time_style}>{format_time_display(row['Start_Time'])}</p>", unsafe_allow_html=True)
                    end_time_display = format_time_display(row['End_Time'])
                    cols[5].markdown(f"<p {time_style}>{end_time_display}</p>", unsafe_allow_html=True)
                    duration_display = format_duration(row['Duration_Minutes'])
                    cols[6].markdown(f"<p {time_style}>{duration_display}</p>", unsafe_allow_html=True)
        
        # -----------------------------------------------------------------
        # 💥 [GSHEETS] ลบส่วนดาวน์โหลด CSV
        # -----------------------------------------------------------------
        st.subheader("ดูข้อมูล")
        st.markdown("ข้อมูลทั้งหมดถูกบันทึกและโหลดมาจาก Google Sheets โดยตรง")
        
        # 💥 [GSHEETS] ลบส่วน Expander ดูข้อมูลดิบ (เพราะมันคือ df ที่แสดงอยู่แล้ว)

# -----------------------------------------------------------------
# 💥 การเรียกใช้งานฟังก์ชันหลัก
# -----------------------------------------------------------------
if __name__ == "__main__":
    main()
