import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timezone, timedelta # เพิ่ม time
import os
import numpy as np
import math
import pathlib
import base64
from streamlit_qrcode_scanner import qrcode_scanner # ต้องมีบรรทัดนี้ด้านบนสุดของไฟล์

# -----------------------------------------------------------------
# กำหนดเส้นทางไฟล์ให้ชี้ไปที่ Desktop (เหมือนเดิม)
# -----------------------------------------------------------------
LOGS_DIR = os.path.join(os.path.expanduser('~'), 'Desktop', 'TimeLogs')
DATA_FILE = os.path.join(LOGS_DIR, "time_logs.csv")
USER_DATA_FILE = os.path.join(LOGS_DIR, "user_data.csv") # 💥 NEW FILE PATH

# -----------------------------------------------------------------
# 💥 แก้ไข: ชื่อคอลัมน์ใหม่
# -----------------------------------------------------------------
CSV_COLUMNS = ['Employee_ID', 'Date', 'Start_Time', 'End_Time', 'Activity_Type', 'Duration_Minutes']


# --- CSS (รวม CSS และ FIX ลดช่องว่างด้านบน) ---
CUSTOM_CSS = """
<style>
/* 1. FIX: ลดพื้นที่ว่างด้านบนสุด */
div.block-container {
    padding-top: 1rem; /* ลดพื้นที่ว่างด้านบน */
    padding-bottom: 0rem;
}

/* 2. สไตล์ปุ่มและตัวอักษร (ชุดเดิม) */
div.stButton > button[kind="secondaryFormSubmit"] { /* ปุ่มลบ */
    padding: 1px 5px !important; font-size: 10px !important; height: 22px !important; line-height: 1 !important;
}
.time-display {
    font-size: 1.1em; font-weight: bold; margin-top: -10px; margin-bottom: -10px;
}
.stForm {
    padding: 10px; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 5px;
}
div.stButton button[data-testid="baseButton-primary"] {
    background-color: #00FFFF !important; border-color: #00FFFF !important; color: black !important;
}
div.stButton button[data-testid="baseButton-primary"]:hover {
    background-color: #33FFFF !important; border-color: #33FFFF !important;
}
div.stButton button[data-testid="baseButton-secondary"] {
    color: #00FFFF !important; border-color: #00FFFF !important;
}
div.stButton button:not([kind="primary"]):not([kind="secondary"]):not([kind="secondaryFormSubmit"]) {
     /* background-color: grey !important; */
}
</style>
"""


# --- 1. ฟังก์ชันจัดการไฟล์ข้อมูล (ชุดเดิม) ---
@st.cache_data
def load_data():
    """โหลดข้อมูลจาก CSV และเตรียม DataFrame สำหรับแสดงผล"""
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            if not df.empty:
                df['Date'] = pd.to_datetime(df['Date']).dt.date.astype(str)
                df['Start_Time'] = df['Start_Time'].astype(str)
                df['End_Time'] = df['End_Time'].astype(str).replace('nan', np.nan)
                df['Duration_Minutes'] = pd.to_numeric(df['Duration_Minutes'], errors='coerce') 
            else:
                 df = pd.DataFrame(columns=CSV_COLUMNS)
            
            for col in CSV_COLUMNS:
                 if col not in df.columns:
                      df[col] = np.nan 

            return df.reindex(columns=CSV_COLUMNS) 

        except pd.errors.EmptyDataError: 
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

    # 💥 NEW: สร้างไฟล์ user_data.csv ถ้าไม่มี
    if not os.path.exists(USER_DATA_FILE):
        df_user = pd.DataFrame(columns=['Employee_ID'])
        df_user.to_csv(USER_DATA_FILE, index=False)


def save_data(df):
    """บันทึก DataFrame ลงในไฟล์ CSV"""
    try:
        for col in CSV_COLUMNS:
            if col not in df.columns:
                df[col] = np.nan
        df = df[CSV_COLUMNS] 
        df.to_csv(DATA_FILE, index=False)
        st.cache_data.clear() 
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {e}")

# -----------------------------------------------------------------
# 💥 NEW: ฟังก์ชันสำหรับจัดการ User Data (ID ที่ไม่ซ้ำ)
# -----------------------------------------------------------------

@st.cache_data
def load_user_data():
    """โหลดข้อมูล ID พนักงานที่ไม่ซ้ำจาก user_data.csv"""
    if os.path.exists(USER_DATA_FILE):
        try:
            df = pd.read_csv(USER_DATA_FILE)
            if 'Employee_ID' not in df.columns:
                 return []
            return df['Employee_ID'].dropna().astype(str).unique().tolist()
        except pd.errors.EmptyDataError:
            return []
        except Exception:
            return []
    return []

def save_unique_user_id(employee_id):
    """บันทึก ID พนักงานใหม่ที่ไม่ซ้ำลงใน user_data.csv"""
    employee_id = str(employee_id) 
    if not employee_id:
        return

    existing_ids = load_user_data()
    
    if employee_id not in existing_ids:
        existing_ids.append(employee_id)
        df_new = pd.DataFrame({'Employee_ID': existing_ids})
        
        try:
            df_new.to_csv(USER_DATA_FILE, index=False)
            st.cache_data.clear() 
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการบันทึก User ID: {e}")

# 💥 NEW: ฟังก์ชันคำนวณ Duration 
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
    df = load_data() 
    
    condition = (df['Employee_ID'] == employee_id) & \
                (df['Date'] == date_str) & \
                (df['End_Time'].isna() | (df['End_Time'].astype(str).str.lower() == 'nan') | (df['End_Time'] == ''))
                
    ongoing_activities = df[condition]

    if not ongoing_activities.empty:
        index_to_update = ongoing_activities.index.max()
        df.loc[index_to_update, 'End_Time'] = end_time_str
        start_time = df.loc[index_to_update, 'Start_Time']
        duration = calculate_duration(start_time, end_time_str)
        df.loc[index_to_update, 'Duration_Minutes'] = duration
        save_data(df)
        return True 
    return False 

# 💥 NEW: ฟังก์ชันเริ่มกิจกรรมใหม่ (รวม Clock Out อันเก่า)
def log_activity_start(employee_id, date_str, start_time_str, activity_type):
    """บันทึกการเริ่มกิจกรรมใหม่ และ Clock Out กิจกรรมเดิม (ถ้ามี)"""
    try:
        clock_out_latest_activity(employee_id, date_str, start_time_str) 
        df = load_data()

        new_row = pd.DataFrame([{
            'Employee_ID': employee_id,
            'Date': date_str,
            'Start_Time': start_time_str,
            'End_Time': np.nan,
            'Activity_Type': activity_type,
            'Duration_Minutes': np.nan
        }])

        df_to_save = pd.concat([df, new_row], ignore_index=True)
        save_data(df_to_save)
        
        save_unique_user_id(employee_id)
        
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
        return datetime.strptime(str(time_str), '%H:%M:%S').strftime('%H:%M')
    except (ValueError, TypeError):
        return str(time_str).split('.')[0] 

def format_duration(minutes):
    """จัดรูปแบบนาทีเป็น HH:MM"""
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


def get_csv_content_with_bom(data_file_path):
    """สร้างลิงก์ดาวน์โหลด CSV พร้อม BOM (สำหรับภาษาไทย)"""
    try:
        with open(data_file_path, "r", encoding='utf-8') as f:
            csv_content = f.read()
        bom = "\ufeff"
        content_with_bom = bom + csv_content
        return content_with_bom
    except FileNotFoundError: return None
    except Exception as e: return None


# -----------------------------------------------------------------
# 💥 NEW: ฟังก์ชัน Callback submit_activity 
# -----------------------------------------------------------------
def submit_activity(activity_type):
    """
    Callback function to handle button clicks, validation, logging,
    and updating session state messages.
    """
    
    # 1. ดึง ID จาก session_state 
    emp_id = st.session_state.get("current_emp_id", "")
    if not emp_id:
        st.session_state.last_message = ("warning", "กรุณาสแกนหรือกรอก Employee ID ก่อนทำกิจกรรม")
        return 

    # 2. ดึงเวลาปัจจุบัน
    THAILAND_TZ = timezone(timedelta(hours=7))
    now_thailand = datetime.now(THAILAND_TZ)
    current_date_str = now_thailand.date().strftime('%Y-%m-%d')
    current_time_str = now_thailand.time().strftime('%H:%M:%S')

    # 3. Logic การบันทึก
    if activity_type == "End_Activity":
        if clock_out_latest_activity(emp_id, current_date_str, current_time_str):
            # 4. ตั้งค่า Message และล้างค่า
            st.session_state.last_message = ("success", f"✅ สิ้นสุดกิจกรรมล่าสุด สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อยแล้ว!")
            st.session_state["current_emp_id"] = "" 
            st.session_state["manual_emp_id_input_outside_form"] = "" 
        else:
            st.session_state.last_message = ("warning", f"⚠️ ไม่พบกิจกรรมที่กำลังดำเนินอยู่สำหรับ ID: **{emp_id}** วันที่ {current_date_str}")
            
    else:
        # (activity_type คือ "Work", "Smoking", "Toilet")
        if log_activity_start(emp_id, current_date_str, current_time_str, activity_type):
            success_message = f"✅ เริ่มกิจกรรม **{activity_type}** สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อยแล้ว!"
            if activity_type == "Work":
                success_message = f"▶️ เริ่มงาน สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อยแล้ว!"
            elif activity_type == "Smoking":
                success_message = f"🚭 เริ่มสูบบุหรี่ สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อยแล้ว!"
            elif activity_type == "Toilet":
                 success_message = f"🚻 เริ่มเข้าห้องน้ำ สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อยแล้ว!"
            
            # 4. ตั้งค่า Message และล้างค่า
            st.session_state.last_message = ("success", success_message)
            st.session_state["current_emp_id"] = "" 
            st.session_state["manual_emp_id_input_outside_form"] = "" 
        else:
            st.session_state.last_message = ("error", f"เกิดข้อผิดพลาดในการเริ่มกิจกรรม {activity_type}")
            
    st.rerun() 


# -----------------------------------------------------------------
# 💥 NEW: ฟังก์ชัน MAIN
# -----------------------------------------------------------------
def main():
    # --- 3. ส่วนหน้าเว็บ (UI) ---
    st.set_page_config(page_title="Time Logger", layout="wide")
    
    # 💥 FIX: ใช้ CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Initialize Session State
    if "current_emp_id" not in st.session_state:
        st.session_state["current_emp_id"] = ""
    if "manual_emp_id_input_outside_form" not in st.session_state: 
        st.session_state["manual_emp_id_input_outside_form"] = ""
    if "last_message" not in st.session_state:
        st.session_state.last_message = None

    # --- 3.1 การเริ่มต้นไฟล์ข้อมูล ---
    initialize_data_file()

    # --- 3.2 โหลดข้อมูล ---
    df = load_data() 


    # -----------------------------------------------------------------
    # --- Layout หลัก ---
    main_col1, main_col2 = st.columns([1, 2])

    with main_col1:
        st.title("ระบบบันทึกเวลากิจกรรม")
        st.markdown(f"**บันทึกข้อมูลที่:** `{LOGS_DIR}`")
        
        # -----------------------------------------------------------------
        # แสดง Message
        # -----------------------------------------------------------------
        if st.session_state.last_message:
            msg_type, msg_content = st.session_state.last_message
            if msg_type == "success":
                st.success(msg_content)
            elif msg_type == "warning":
                st.warning(msg_content)
            elif msg_type == "error":
                st.error(msg_content)
            st.session_state.last_message = None 
        
        # -----------------------------------------------------------------
        st.subheader("บันทึกกิจกรรม")

        # 1. กล่องกรอก ID ด้วยมือ (Manual Input)
        manual_input_value = st.session_state["manual_emp_id_input_outside_form"]
        
        manual_input = st.text_input(
            "กรอก ID ด้วยมือ:", 
            value=manual_input_value,
            key="manual_emp_id_input_outside_form", 
            placeholder="กรอก ID ที่นี่"
        )

        # Logic: ถ้ามีการกรอก Manual Input ให้ค่านี้แทนที่ใน session_state 
        if manual_input != st.session_state.current_emp_id:
            st.session_state["current_emp_id"] = manual_input
        
        emp_id_input = st.session_state.current_emp_id
            
        # -----------------------------------------------------------------
        # 💥 FIX: 2. ส่วน Form/ปุ่มกิจกรรม (ย้ายมาไว้ข้างล่าง Manual Input)
        # -----------------------------------------------------------------
        
        with st.form("activity_form", clear_on_submit=False): 
            
            if emp_id_input:
                st.info(f"ID ที่ใช้บันทึก: **{emp_id_input}**")
            else:
                st.info("กรุณาสแกนหรือกรอก Employee ID ก่อนทำกิจกรรม")

            st.write("เลือกกิจกรรม:")
            
            activity_buttons_col1, activity_buttons_col2, activity_buttons_col3, activity_buttons_col4 = st.columns(4)

            is_disabled = not bool(emp_id_input) 
            
            # ปุ่มกิจกรรม (ใช้ on_click)
            submitted_work = activity_buttons_col1.form_submit_button("เริ่มกิจกรรม", type="primary", use_container_width=True, disabled=is_disabled,
                                                                    on_click=submit_activity, args=("Work",))
            submitted_smoking = activity_buttons_col2.form_submit_button("สูบบุหรี่", use_container_width=True, disabled=is_disabled,
                                                                       on_click=submit_activity, args=("Smoking",))
            submitted_toilet = activity_buttons_col3.form_submit_button("เข้าห้องน้ำ", use_container_width=True, disabled=is_disabled,
                                                                      on_click=submit_activity, args=("Toilet",))
            submitted_end_activity = activity_buttons_col4.form_submit_button("สิ้นสุดกิจกรรม", type="secondary", use_container_width=True, disabled=is_disabled,
                                                                           on_click=submit_activity, args=("End_Activity",))

        # -----------------------------------------------------------------
        # 💥 FIX: 3. กล้องสแกน QR Code (ย้ายไปอยู่ด้านล่างสุด)
        # -----------------------------------------------------------------
        st.write("---") # เส้นคั่นก่อนส่วนสแกน
        st.write("หรือ สแกน QR/Barcode:")
        
        # 3. QR Code Scanner: Component ที่เปิดกล้อง
        scanned_id = qrcode_scanner(key="qrcode_scanner_key_new")
        
        # Logic: ถ้าสแกนได้ ให้บันทึกค่าลง session_state ทันที
        # เนื่องจาก logic นี้ถูกย้ายมาอยู่ด้านล่างสุดแล้ว มันจะทำงานหลังจาก form ถูกประมวลผล
        if scanned_id and scanned_id != st.session_state.current_emp_id:
            st.session_state["current_emp_id"] = scanned_id
            st.session_state["manual_emp_id_input_outside_form"] = scanned_id # Sync ให้ input แสดงค่า
            st.rerun()


    # -----------------------------------------------------------------
    # ส่วนคอลัมน์ขวา (แสดงข้อมูล)
    # -----------------------------------------------------------------
    with main_col2:
        st.markdown("---")
        st.subheader("ข้อมูลลงเวลา")

        # --- ส่วน Filter (เหมือนเดิม) ---
        col_filter1, col_filter2, col_filter3 = st.columns(3)

        filter_date_from = col_filter1.date_input("กรองตามวันที่ (From)", value=datetime.now().date(), key="date_from_key")
        filter_date_to = col_filter2.date_input("กรองตามวันที่ (To)", value=datetime.now().date(), key="date_to_key")

        unique_ids = ["All"] + sorted(load_user_data())
        filter_id = col_filter3.selectbox("กรองตาม Employee ID", options=unique_ids, key="id_filter_key")


        # --- สร้างตารางแสดงผล ---
        if df.empty:
            st.info("ยังไม่มีข้อมูลการลงเวลา")
        else:
            display_df = df.copy()
            display_df['Original_Index'] = display_df.index
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
                    original_index = row['Original_Index']
                    cols = st.columns(col_ratios)
                    time_style = "class='time-display'"
                    if cols[0].button("❌", key=f"del_{original_index}_{index}", on_click=delete_log_entry, args=(original_index,), help="ลบ Log ลงเวลานี้"):
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
            try:
                raw_df_display = pd.read_csv(DATA_FILE)
                st.dataframe(raw_df_display)
            except FileNotFoundError:
                st.warning("ยังไม่มีไฟล์ข้อมูล")
            except Exception as e:
                st.error(f"ไม่สามารถโหลดข้อมูลดิบได้: {e}")

# -----------------------------------------------------------------
# 💥 การเรียกใช้งานฟังก์ชันหลัก
# -----------------------------------------------------------------
if __name__ == "__main__":
    main()
