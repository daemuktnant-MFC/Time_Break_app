import streamlit as st
import pandas as pd
from datetime import datetime, date, time # เพิ่ม time
import os
import numpy as np
import math
import pathlib
import base64

# -----------------------------------------------------------------
# กำหนดเส้นทางไฟล์ให้ชี้ไปที่ Desktop (เหมือนเดิม)
# -----------------------------------------------------------------
LOGS_DIR = os.path.join(os.path.expanduser('~'), 'Desktop', 'TimeLogs')
DATA_FILE = os.path.join(LOGS_DIR, "time_logs.csv")

# -----------------------------------------------------------------
# 💥 แก้ไข: ชื่อคอลัมน์ใหม่
# -----------------------------------------------------------------
CSV_COLUMNS = ['Employee_ID', 'Date', 'Start_Time', 'End_Time', 'Activity_Type', 'Duration_Minutes']


# --- CSS (เหมือนเดิม เพิ่มนิดหน่อยสำหรับปุ่มใหม่) ---
CUSTOM_CSS = """
<style>
/* ... (CSS เดิม) ... */
div.stButton > button[kind="secondaryFormSubmit"] { /* ปุ่มลบ */
    padding: 1px 5px !important; font-size: 10px !important; height: 22px !important; line-height: 1 !important;
}
.time-display {
    font-size: 1.1em; font-weight: bold; margin-top: -10px; margin-bottom: -10px;
}
.stForm {
    padding: 10px; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 5px;
}

/* ปุ่ม Primary (Clock In) */
div.stButton button[data-testid="baseButton-primary"] {
    background-color: #00FFFF !important; border-color: #00FFFF !important; color: black !important;
}
div.stButton button[data-testid="baseButton-primary"]:hover {
    background-color: #33FFFF !important; border-color: #33FFFF !important;
}
/* ปุ่ม Secondary (Clock Out) */
div.stButton button[data-testid="baseButton-secondary"] {
    color: #00FFFF !important; border-color: #00FFFF !important;
}
/* 💥 NEW: สไตล์สำหรับปุ่มกิจกรรม (Smoking, Toilet) - ใช้สีเทา */
div.stButton button:not([kind="primary"]):not([kind="secondary"]):not([kind="secondaryFormSubmit"]) {
     /* background-color: grey !important; */ /* Option: ทำให้พื้นหลังเทา */
     /* border-color: grey !important; */
     /* color: white !important; */
}
</style>
"""


# --- 1. ฟังก์ชันจัดการไฟล์ข้อมูล (ปรับปรุงใหม่) ---

@st.cache_data
def load_data():
    """โหลดข้อมูลจาก CSV และเตรียม DataFrame สำหรับแสดงผล"""
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            if not df.empty:
                df['Date'] = pd.to_datetime(df['Date']).dt.date.astype(str)
                # แปลงเวลาเป็น string เพื่อแสดงผล, จัดการ NaN
                df['Start_Time'] = df['Start_Time'].astype(str)
                df['End_Time'] = df['End_Time'].astype(str).replace('nan', np.nan)
                df['Duration_Minutes'] = pd.to_numeric(df['Duration_Minutes'], errors='coerce') # แปลงเป็นตัวเลข, ถ้า Error ให้เป็น NaN
            else:
                 # กรณีไฟล์มีแต่ Header
                 df = pd.DataFrame(columns=CSV_COLUMNS)
            
            # ตรวจสอบคอลัมน์
            for col in CSV_COLUMNS:
                 if col not in df.columns:
                      df[col] = np.nan # เพิ่มคอลัมน์ที่ขาดไป

            return df.reindex(columns=CSV_COLUMNS) # จัดเรียงและคืนค่า

        except pd.errors.EmptyDataError: # กรณีไฟล์ว่างเปล่า
             return pd.DataFrame(columns=CSV_COLUMNS)
        except Exception as e:
             st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
             return pd.DataFrame(columns=CSV_COLUMNS)

    return pd.DataFrame(columns=CSV_COLUMNS)


def initialize_data_file():
    """สร้างโฟลเดอร์และไฟล์ CSV หากยังไม่มี"""
    try:
        pathlib.Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        st.error(f"ไม่สามารถสร้างโฟลเดอร์ได้: {LOGS_DIR}. โปรดตรวจสอบสิทธิ์การเข้าถึง.")
        st.stop()

    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=CSV_COLUMNS)
        df.to_csv(DATA_FILE, index=False)
        st.info(f"สร้างไฟล์ {DATA_FILE} เรียบร้อยแล้ว")


def save_data(df):
    """บันทึก DataFrame ลงในไฟล์ CSV"""
    try:
        # ตรวจสอบให้แน่ใจว่ามีทุกคอลัมน์ก่อนบันทึก
        for col in CSV_COLUMNS:
            if col not in df.columns:
                df[col] = np.nan
        df = df[CSV_COLUMNS] # จัดเรียงคอลัมน์ให้ตรง
        df.to_csv(DATA_FILE, index=False)
        st.cache_data.clear() # ล้าง Cache เพื่อโหลดข้อมูลใหม่
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {e}")

# 💥 NEW: ฟังก์ชันคำนวณ Duration (ย้ายมาไว้ตรงนี้)
def calculate_duration(start_time_str, end_time_str):
    """คำนวณระยะเวลาเป็นนาที"""
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

# 💥 NEW: ฟังก์ชัน Clock Out กิจกรรมล่าสุด
def clock_out_latest_activity(employee_id, date_str, end_time_str):
    """ค้นหาและ Clock Out กิจกรรมล่าสุดที่ยังเปิดอยู่"""
    df = load_data() # โหลดข้อมูลล่าสุด
    
    # Filter หากิจกรรมของพนักงานคนนี้ในวันนี้ที่ยังไม่มี End_Time
    condition = (df['Employee_ID'] == employee_id) & \
                (df['Date'] == date_str) & \
                (df['End_Time'].isna() | (df['End_Time'].astype(str).str.lower() == 'nan') | (df['End_Time'] == ''))
                
    ongoing_activities = df[condition]

    if not ongoing_activities.empty:
        # หากิจกรรมล่าสุด (index สูงสุด)
        index_to_update = ongoing_activities.index.max()
        
        # อัปเดต End_Time
        df.loc[index_to_update, 'End_Time'] = end_time_str
        
        # คำนวณและอัปเดต Duration
        start_time = df.loc[index_to_update, 'Start_Time']
        duration = calculate_duration(start_time, end_time_str)
        df.loc[index_to_update, 'Duration_Minutes'] = duration
        
        save_data(df)
        return True # Clock Out สำเร็จ
    return False # ไม่มีกิจกรรมที่ต้อง Clock Out

# 💥 NEW: ฟังก์ชันเริ่มกิจกรรมใหม่ (รวม Clock Out อันเก่า)
def log_activity_start(employee_id, date_str, start_time_str, activity_type):
    """บันทึกการเริ่มกิจกรรมใหม่ และ Clock Out กิจกรรมเดิม (ถ้ามี)"""
    try:
        # 1. Clock Out กิจกรรมเดิมก่อน
        clock_out_latest_activity(employee_id, date_str, start_time_str) # ใชเวลาเริ่มใหม่เป็นเวลาจบของอันเก่า

        # 2. โหลดข้อมูลล่าสุด (อาจมีการเปลี่ยนแปลงจากการ Clock Out)
        df = load_data()

        # 3. สร้างแถวใหม่สำหรับกิจกรรมนี้
        new_row = pd.DataFrame([{
            'Employee_ID': employee_id,
            'Date': date_str,
            'Start_Time': start_time_str,
            'End_Time': np.nan,
            'Activity_Type': activity_type,
            'Duration_Minutes': np.nan
        }])

        # 4. บันทึกข้อมูล
        df_to_save = pd.concat([df, new_row], ignore_index=True)
        save_data(df_to_save)
        return True
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเริ่มกิจกรรม {activity_type}: {e}")
        return False


def delete_log_entry(original_index):
    """ลบ Log ตาม Index เดิม"""
    df = load_data()
    if original_index in df.index:
        df = df.drop(index=original_index)
        save_data(df)
    else:
        st.warning(f"ไม่พบ Index {original_index} ที่จะลบ")


# --- 2. ฟังก์ชันคำนวณและแสดงผล ---

def format_time_display(time_str):
    """จัดรูปแบบเวลาเป็น HH:MM"""
    if pd.isnull(time_str) or str(time_str).lower() == 'nan':
        return "N/A"
    try:
        # ลองแปลงจาก HH:MM:SS
        return datetime.strptime(str(time_str), '%H:%M:%S').strftime('%H:%M')
    except (ValueError, TypeError):
        # ถ้า Error อาจเป็น HH:MM อยู่แล้ว หรือรูปแบบอื่น
        return str(time_str).split('.')[0] # ตัด .0 ถ้ามี

def format_duration(minutes):
    """จัดรูปแบบนาทีเป็น HH:MM"""
    if pd.isnull(minutes) or (isinstance(minutes, float) and math.isnan(minutes)):
        return "N/A"
    try:
        minutes = int(float(minutes)) # แปลงเป็น float ก่อน เผื่อเป็น string "120.0"
    except (ValueError, TypeError):
        return "N/A" # ถ้าแปลงไม่ได้

    if minutes < 0:
        return "00:00"

    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"


# ฟังก์ชันสร้างลิงก์ดาวน์โหลด (เหมือนเดิม)
def get_csv_content_with_bom(data_file_path):
    # ... (โค้ดเดิม) ...
    try:
        with open(data_file_path, "r", encoding='utf-8') as f:
            csv_content = f.read()
        bom = "\ufeff"
        content_with_bom = bom + csv_content
        return content_with_bom
    except FileNotFoundError: return None
    except Exception as e: return None

# --- 3. ส่วนหน้าเว็บ (UI) ---

st.set_page_config(page_title="Time Logger", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --- 3.1 การเริ่มต้นไฟล์ข้อมูล ---
initialize_data_file()

# --- 3.2 โหลดข้อมูล ---
df = load_data() # df ที่โหลดมาตอนนี้มีคอลัมน์ครบตาม CSV_COLUMNS


# -----------------------------------------------------------------
# 💥 3. ส่วน Header: ปรับปรุง Form และปุ่ม
# -----------------------------------------------------------------
header_col1, header_col2 = st.columns([1.5, 1])

with header_col1:
    st.title("ระบบบันทึกเวลากิจกรรม")
    st.markdown(f"**บันทึกข้อมูลที่:** `{LOGS_DIR}`")


with header_col2:
    with st.form("activity_form", clear_on_submit=True):
        st.subheader("บันทึกกิจกรรม")

        # Input ID ยังคงจำเป็น
        emp_id_input = st.text_input("Employee ID (Scan/Key In)", key="emp_id_input_key")

        # 💥 NEW: แถวปุ่มกิจกรรม
        st.write("เลือกกิจกรรม:")
        activity_buttons_col1, activity_buttons_col2, activity_buttons_col3, activity_buttons_col4 = st.columns(4)

        submitted_work = activity_buttons_col1.form_submit_button("เริ่มกิจกรรม", type="primary", use_container_width=True)
        submitted_smoking = activity_buttons_col2.form_submit_button("สูบบุหรี่", use_container_width=True)
        submitted_toilet = activity_buttons_col3.form_submit_button("เข้าห้องน้ำ", use_container_width=True)
        submitted_end_activity = activity_buttons_col4.form_submit_button("สิ้นสุดกิจกรรม", type="secondary", use_container_width=True) # ปุ่ม Clock Out หลัก

        # วันที่และเวลาปัจจุบัน (ใช้เมื่อกดปุ่ม)
        current_date_str = datetime.now().date().strftime('%Y-%m-%d')
        current_time_str = datetime.now().time().strftime('%H:%M:%S')

        # --- Logic การกดปุ่ม ---
        if submitted_work or submitted_smoking or submitted_toilet or submitted_end_activity:
            if not emp_id_input:
                st.warning("กรุณาใส่ Employee ID")
                st.stop()

            activity_to_log = None
            success_message = ""

            # ปุ่มเริ่มกิจกรรม
            if submitted_work:
                activity_to_log = "Break"
                success_message = f"✅ เริ่มกิจกรรม สำหรับ ID: **{emp_id_input}** เวลา {current_time_str} เรียบร้อย!"
            elif submitted_smoking:
                activity_to_log = "Smoking"
                success_message = f"🚭 เริ่มสูบบุหรี่ สำหรับ ID: **{emp_id_input}** เวลา {current_time_str} เรียบร้อย!"
            elif submitted_toilet:
                activity_to_log = "Toilet"
                success_message = f"🚻 เริ่มเข้าห้องน้ำ สำหรับ ID: **{emp_id_input}** เวลา {current_time_str} เรียบร้อย!"

            # ถ้ามีการกดปุ่มเริ่มกิจกรรม
            if activity_to_log:
                if log_activity_start(emp_id_input, current_date_str, current_time_str, activity_to_log):
                    st.success(success_message)
                    st.rerun()
                else:
                    # อาจมี Error อื่นๆ เกิดขึ้นภายใน log_activity_start
                    st.error("เกิดข้อผิดพลาดในการบันทึก")
                    st.rerun() # ให้แสดง Error

            # ปุ่มสิ้นสุดกิจกรรม (Clock Out)
            elif submitted_end_activity:
                if clock_out_latest_activity(emp_id_input, current_date_str, current_time_str):
                    st.success(f"✅ สิ้นสุดกิจกรรมล่าสุด สำหรับ ID: **{emp_id_input}** เวลา {current_time_str} เรียบร้อย!")
                    st.rerun()
                else:
                    st.warning(f"⚠️ ไม่พบกิจกรรมที่กำลังดำเนินอยู่สำหรับ ID: **{emp_id_input}** วันที่ {current_date_str}")
                    st.rerun() # ให้แสดง Warning

st.markdown("---")

# 💥 3.4 ส่วนแสดงผลข้อมูล (หน้าหลัก)

st.subheader("ข้อมูลลงเวลา")

# --- ส่วน Filter (เหมือนเดิม) ---
col_filter1, col_filter2, col_filter3 = st.columns(3)

filter_date_from = col_filter1.date_input(
    "กรองตามวันที่ (From)",
    value=datetime.now().date() - pd.Timedelta(days=30),
    key="date_from_key"
)

filter_date_to = col_filter2.date_input(
    "กรองตามวันที่ (To)",
    value=datetime.now().date(),
    key="date_to_key"
)

unique_ids = ["All"]
if not df.empty and 'Employee_ID' in df.columns:
    unique_ids += sorted(df['Employee_ID'].dropna().unique())
filter_id = col_filter3.selectbox("กรองตาม Employee ID", options=unique_ids, key="id_filter_key")

# --- สร้างตารางแสดงผล ---
if df.empty:
    st.info("ยังไม่มีข้อมูลการลงเวลา")
else:
    display_df = df.copy()
    display_df['Original_Index'] = display_df.index # เก็บ Index เดิมไว้เสมอ

    # แปลง Date เป็น Object เพื่อ Filter
    display_df['Date_Obj'] = pd.to_datetime(display_df['Date']).dt.date

    # Logic การกรอง
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
        st.stop()

    display_df = display_df.drop(columns=['Date_Obj'], errors='ignore')

    # จัดเรียงข้อมูลตามวันที่และเวลาล่าสุดก่อนแสดงผล
    display_df = display_df.sort_values(by=['Date', 'Start_Time'], ascending=[False, False])

    display_df = display_df.reset_index(drop=True) # Reset index สำหรับการแสดงผล

    # --- ส่วนหัวตาราง ---
    # 💥 แก้ไข: ปรับเป็น 7 คอลัมน์ [ลบ, ID, Date, Activity, Start, End, Duration]
    col_ratios = [0.5, 1, 1, 1.2, 1, 1, 1.3]
    cols = st.columns(col_ratios)

    # 💥 แก้ไข Header
    headers = ["ลบ", "Employee ID", "Date", "ประเภทกิจกรรม", "เวลาเริ่ม", "เวลาสิ้นสุด", "**ระยะเวลา**"]
    for col, header in zip(cols, headers):
        col.markdown(f"**{header}**")
    st.markdown("---")

    # --- วนลูปแสดงข้อมูล ---
    for index, row in display_df.iterrows(): # ใช้ index จาก display_df ที่ reset แล้ว
        # ใช้ Original_Index ที่เก็บไว้ในการอ้างอิงข้อมูลเดิม
        original_index = row['Original_Index']

        cols = st.columns(col_ratios)
        time_style = "class='time-display'"

        # คอลัมน์ 0: ปุ่มลบ
        if cols[0].button(
            "❌",
            key=f"del_{original_index}_{index}", # เพิ่ม index เพื่อให้ key ไม่ซ้ำ
            on_click=delete_log_entry,
            args=(original_index,), # ส่ง Original Index ไปลบ
            help="ลบ Log ลงเวลานี้"
        ):
             st.rerun()

        # คอลัมน์ 1 - 2: ข้อมูลมาตรฐาน (ID, Date)
        cols[1].write(row['Employee_ID'])
        cols[2].write(row['Date'])

        # 💥 คอลัมน์ 3: ประเภทกิจกรรม
        cols[3].write(row['Activity_Type'])

        # คอลัมน์ 4: เวลาเริ่ม (Start Time)
        cols[4].markdown(f"<p {time_style}>{format_time_display(row['Start_Time'])}</p>", unsafe_allow_html=True)

        # คอลัมน์ 5: เวลาสิ้นสุด (End Time)
        end_time_display = format_time_display(row['End_Time'])
        cols[5].markdown(f"<p {time_style}>{end_time_display}</p>", unsafe_allow_html=True)

        # คอลัมน์ 6: ระยะเวลา (Duration)
        duration_display = format_duration(row['Duration_Minutes'])
        cols[6].markdown(f"<p {time_style}>{duration_display}</p>", unsafe_allow_html=True)

    st.markdown("---")

# -----------------------------------------------------------------
# ส่วนสร้างปุ่มดาวน์โหลดไฟล์
# -----------------------------------------------------------------
st.subheader("ดาวน์โหลดข้อมูล")

csv_data = get_csv_content_with_bom(DATA_FILE)

if csv_data:
    st.download_button(
        label="Download Log File (.csv)",
        data=csv_data,
        file_name=os.path.basename(DATA_FILE),
        mime="text/csv",
        key="download_button_key"
    )

# (Optional) ส่วนแสดงข้อมูลดิบ
with st.expander(f"ดูข้อมูลดิบ (Raw Data from: {DATA_FILE})"):
    # 💥 โหลดไฟล์ดิบมาแสดงผล
    try:
        raw_df_display = pd.read_csv(DATA_FILE)
        st.dataframe(raw_df_display)
    except FileNotFoundError:
        st.warning("ยังไม่มีไฟล์ข้อมูล")
    except Exception as e:
        st.error(f"ไม่สามารถโหลดข้อมูลดิบได้: {e}")
