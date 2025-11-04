import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timezone, timedelta # เพิ่ม time
import os
import numpy as np
import math
import pathlib
import base64
from streamlit_qrcode_scanner import qrcode_scanner
import sqlalchemy # ต้องติดตั้ง: pip install sqlalchemy

# -----------------------------------------------------------------
# 💥 FIX: ลบการกำหนดเส้นทางไฟล์ CSV ทิ้ง
# -----------------------------------------------------------------
# (Paths to LOGS_DIR, DATA_FILE, USER_DATA_FILE ถูกลบออก)

# -----------------------------------------------------------------
# 💥 FIX: ชื่อคอลัมน์ SQL (ตัวพิมพ์เล็ก)
# -----------------------------------------------------------------
SQL_COLS_TIME_LOGS = ['employee_id', 'date', 'start_time', 'end_time', 'activity_type', 'duration_minutes']
SQL_COLS_USERS = ['employee_id']


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


# --- 1. ฟังก์ชันจัดการฐานข้อมูล (SQL Version) ---

def initialize_database():
    """สร้างตารางในฐานข้อมูลหากยังไม่มี"""
    try:
        conn = st.connection("db_connection_name", type="sql")
        
        with conn.session as s:
            s.execute(sqlalchemy.text("""
            CREATE TABLE IF NOT EXISTS time_logs (
                id SERIAL PRIMARY KEY,
                employee_id VARCHAR(255),
                date DATE,
                start_time TIME,
                end_time TIME,
                activity_type VARCHAR(50),
                duration_minutes FLOAT
            );
            """))
            s.execute(sqlalchemy.text("""
            CREATE TABLE IF NOT EXISTS users (
                employee_id VARCHAR(255) PRIMARY KEY
            );
            """))
            s.commit()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อหรือสร้างตารางฐานข้อมูล: {e}")
        st.stop()

@st.cache_data(ttl=15) # Cache 15 วินาที
def load_data():
    """โหลดข้อมูลจาก SQL Database"""
    try:
        conn = st.connection("db_connection_name", type="sql")
        df = conn.query("SELECT id AS Original_Index, * FROM time_logs ORDER BY date DESC, start_time DESC", 
                        columns=SQL_COLS_TIME_LOGS + ['Original_Index'])
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.date.astype(str)
            df['start_time'] = df['start_time'].astype(str)
            df['end_time'] = df['end_time'].astype(str).replace('NaT', np.nan)
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล (load_data): {e}")
        return pd.DataFrame(columns=SQL_COLS_TIME_LOGS + ['Original_Index'])

@st.cache_data(ttl=60) # Cache 1 นาที
def load_user_data():
    """โหลด ID พนักงานที่ไม่ซ้ำจาก SQL Database"""
    try:
        conn = st.connection("db_connection_name", type="sql")
        df = conn.query("SELECT employee_id FROM users ORDER BY employee_id ASC", columns=SQL_COLS_USERS)
        return df['employee_id'].dropna().astype(str).unique().tolist()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลด User (load_user_data): {e}")
        return []

def save_unique_user_id(employee_id):
    """บันทึก ID พนักงานใหม่ที่ไม่ซ้ำ"""
    employee_id = str(employee_id)
    if not employee_id:
        return
    
    try:
        conn = st.connection("db_connection_name", type="sql")
        with conn.session as s:
            s.execute(sqlalchemy.text("""
            INSERT INTO users (employee_id)
            VALUES (:id)
            ON CONFLICT (employee_id) DO NOTHING;
            """), params=dict(id=employee_id))
            s.commit()
        st.cache_data.clear() 
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึก User ID: {e}")

# (ฟังก์ชัน calculate_duration, clock_out_latest_activity, log_activity_start, delete_log_entry,
# format_time_display, format_duration, get_csv_content_with_bom... ทั้งหมดเหมือนเดิม
# ...คัดลอกมาวางที่นี่...)

# 💥 NEW: ฟังก์ชันคำนวณ Duration 
def calculate_duration(start_time_str, end_time_str):
    """คำนวณระยะเวลาเป็นนาที"""
    try:
        if pd.isnull(start_time_str) or pd.isnull(end_time_str) or str(start_time_str).lower() == 'nat' or str(end_time_str).lower() == 'nat':
            return np.nan

        date_time_format = '%H:%M:%S'
        t_start_time = datetime.strptime(str(start_time_str), date_time_format).time()
        t_end_time = datetime.strptime(str(end_time_str), date_time_format).time()

        base_date = datetime(2000, 1, 1)
        t_start = datetime.combine(base_date, t_start_time)
        t_end = datetime.combine(base_date, t_end_time)

        if t_end < t_start:
            t_end += pd.Timedelta(days=1)

        duration_minutes = (t_end - t_start).total_seconds() / 60
        return max(0, duration_minutes)
    except (ValueError, TypeError, AttributeError):
        return np.nan

# 💥 FIX: ฟังก์ชัน Clock Out (เขียนใหม่สำหรับ SQL)
def clock_out_latest_activity(employee_id, date_str, end_time_obj): # รับเป็น time object
    """ค้นหาและ Clock Out กิจกรรมล่าสุด (SQL)"""
    try:
        conn = st.connection("db_connection_name", type="sql")
        
        # 1. ค้นหาแถวที่ยังเปิดอยู่ล่าสุด
        query_find = sqlalchemy.text("""
            SELECT id, start_time FROM time_logs
            WHERE employee_id = :id AND date = :date AND end_time IS NULL
            ORDER BY start_time DESC
            LIMIT 1;
        """)
        
        result_df = conn.query(query_find, params=dict(id=employee_id, date=date_str), ttl=0) # No cache

        if not result_df.empty:
            row_to_update = result_df.iloc[0]
            log_id = int(row_to_update['id'])
            start_time_str = str(row_to_update['start_time'])
            
            # 2. คำนวณ Duration
            end_time_str = end_time_obj.strftime('%H:%M:%S')
            duration = calculate_duration(start_time_str, end_time_str)

            # 3. อัปเดตแถวนั้น
            query_update = sqlalchemy.text("""
                UPDATE time_logs
                SET end_time = :end_time, duration_minutes = :duration
                WHERE id = :log_id;
            """)
            
            with conn.session as s:
                s.execute(query_update, params=dict(end_time=end_time_obj, duration=duration, log_id=log_id))
                s.commit()
            
            st.cache_data.clear() # ล้าง Cache load_data
            return True
        
        return False # ไม่มีกิจกรรมที่ต้อง Clock Out
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดใน clock_out_latest_activity: {e}")
        return False

# 💥 FIX: ฟังก์ชันเริ่มกิจกรรมใหม่ (เขียนใหม่สำหรับ SQL)
def log_activity_start(employee_id, date_obj, start_time_obj, activity_type): # รับเป็น object
    """บันทึกการเริ่มกิจกรรมใหม่ (SQL)"""
    try:
        # 1. Clock Out กิจกรรมเดิมก่อน (ตอนนี้ clock_out รับ time object)
        clock_out_latest_activity(employee_id, date_obj.strftime('%Y-%m-%d'), start_time_obj) 

        # 2. บันทึก ID พนักงาน (ถ้ายังไม่มี)
        save_unique_user_id(employee_id)
        
        # 3. เพิ่มแถวใหม่ (INSERT)
        conn = st.connection("db_connection_name", type="sql")
        query_insert = sqlalchemy.text("""
            INSERT INTO time_logs (employee_id, date, start_time, activity_type, end_time, duration_minutes)
            VALUES (:id, :date, :start, :activity, NULL, NULL);
        """)
        
        with conn.session as s:
            s.execute(query_insert, params=dict(
                id=employee_id,
                date=date_obj,
                start=start_time_obj,
                activity=activity_type
            ))
            s.commit()

        st.cache_data.clear() # ล้าง Cache load_data
        return True
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเริ่มกิจกรรม (log_activity_start): {e}")
        return False


def delete_log_entry(original_index):
    """ลบ Log ตาม Index (id)"""
    try:
        conn = st.connection("db_connection_name", type="sql")
        query_delete = sqlalchemy.text("DELETE FROM time_logs WHERE id = :id_to_delete;")
        
        with conn.session as s:
            s.execute(query_delete, params=dict(id_to_delete=original_index))
            s.commit()
        
        st.cache_data.clear()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการลบ Log: {e}")


# --- 2. ฟังก์ชันคำนวณและแสดงผล ---

def format_time_display(time_str):
    if pd.isnull(time_str) or str(time_str).lower() == 'nat':
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
    if minutes < 0: return "00:00"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"


def get_csv_content_with_bom(df_to_download): # 💥 FIX: รับ DataFrame
    """สร้างลิงก์ดาวน์โหลด CSV พร้อม BOM (สำหรับภาษาไทย)"""
    try:
        csv_content = df_to_download.to_csv(index=False)
        bom = "\ufeff"
        content_with_bom = bom + csv_content
        return content_with_bom
    except Exception as e: 
        st.error(f"Error creating CSV: {e}")
        return None

# -----------------------------------------------------------------
# 💥 NEW: ฟังก์ชัน Cleanup ข้อมูลเก่า (30 วัน)
# -----------------------------------------------------------------
def run_daily_cleanup(cutoff_date):
    """ลบข้อมูล time_logs ที่เก่ากว่า cutoff_date"""
    try:
        conn = st.connection("db_connection_name", type="sql")
        query = sqlalchemy.text("DELETE FROM time_logs WHERE date < :cutoff")
        
        with conn.session as s:
            result = s.execute(query, params=dict(cutoff=cutoff_date))
            s.commit()
        
        # ล้าง Cache ทั้งหมดเพื่อให้แน่ใจว่าข้อมูลที่แสดงผลถูกต้อง
        st.cache_data.clear()
        
        # (Optional) แสดง Toast เมื่อทำความสะอาดเสร็จ
        if result.rowcount > 0:
            st.toast(f"🧹 ลบข้อมูล Log เก่า (ก่อนวันที่ {cutoff_date}) จำนวน {result.rowcount} แถวเรียบร้อยแล้ว")
        
    except Exception as e:
        # ไม่ใช้ st.error เพราะไม่ต้องการให้แอปหยุดทำงาน
        print(f"Cleanup Error: {e}")


# -----------------------------------------------------------------
# 💥 NEW: ฟังก์ชัน Callback submit_activity 
# -----------------------------------------------------------------
def submit_activity(activity_type):
    """Callback function (SQL Version)"""
    
    emp_id = st.session_state.get("current_emp_id", "")
    if not emp_id:
        st.session_state.last_message = ("warning", "กรุณาสแกนหรือกรอก Employee ID ก่อนทำกิจกรรม")
        return 

    THAILAND_TZ = timezone(timedelta(hours=7))
    now_thailand = datetime.now(THAILAND_TZ)
    current_date_obj = now_thailand.date() # Date Object
    current_time_obj = now_thailand.time() # Time Object

    if activity_type == "End_Activity":
        if clock_out_latest_activity(emp_id, current_date_obj.strftime('%Y-%m-%d'), current_time_obj):
            st.session_state.last_message = ("success", f"✅ สิ้นสุดกิจกรรมล่าสุด สำหรับ ID: **{emp_id}** เวลา {current_time_obj.strftime('%H:%M:%S')} เรียบร้อยแล้ว!")
            st.session_state["current_emp_id"] = "" 
        else:
            st.session_state.last_message = ("warning", f"⚠️ ไม่พบกิจกรรมที่กำลังดำเนินอยู่สำหรับ ID: **{emp_id}** วันที่ {current_date_obj.strftime('%Y-%m-%d')}")
            
    else:
        # (activity_type คือ "Break", "Smoking", "Toilet")
        if log_activity_start(emp_id, current_date_obj, current_time_obj, activity_type):
            success_message = f"▶️ เริ่มพักเบรค สำหรับ ID: **{emp_id}** เวลา {current_time_obj.strftime('%H:%M:%S')} เรียบร้อยแล้ว!"
            if activity_type == "Smoking":
                success_message = f"🚭 เริ่มสูบบุหรี่ สำหรับ ID: **{emp_id}** เวลา {current_time_obj.strftime('%H:%M:%S')} เรียบร้อยแล้ว!"
            elif activity_type == "Toilet":
                 success_message = f"🚻 เริ่มเข้าห้องน้ำ สำหรับ ID: **{emp_id}** เวลา {current_time_obj.strftime('%H:%M:%S')} เรียบร้อยแล้ว!"
            
            st.session_state.last_message = ("success", success_message)
            st.session_state["current_emp_id"] = "" 
        else:
            st.session_state.last_message = ("error", f"เกิดข้อผิดพลาดในการเริ่มพักเบรค {activity_type}")
            
    st.rerun() 


# -----------------------------------------------------------------
# 💥 NEW: ฟังก์ชัน MAIN
# -----------------------------------------------------------------
def main():
    st.set_page_config(page_title="Time Logger", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Initialize Session State
    if "current_emp_id" not in st.session_state:
        st.session_state["current_emp_id"] = ""
    if "last_message" not in st.session_state:
        st.session_state.last_message = None
    # 💥 NEW: เพิ่ม State สำหรับติดตามการ Cleanup
    if "last_cleanup_date" not in st.session_state:
        st.session_state.last_cleanup_date = None

    # --- 3.1 การเริ่มต้นไฟล์ข้อมูล ---
    initialize_database() # 💥 FIX: เรียกใช้ฟังก์ชัน SQL

    # -----------------------------------------------------------------
    # 💥 NEW: Logic การลบข้อมูลเก่า (Cleanup)
    # -----------------------------------------------------------------
    THAILAND_TZ = timezone(timedelta(hours=7))
    today_str = datetime.now(THAILAND_TZ).date().strftime('%Y-%m-%d')

    # ตรวจสอบว่าวันนี้ได้ลบข้อมูลไปหรือยัง
    if st.session_state.last_cleanup_date != today_str:
        # กำหนดวันที่ตัดข้อมูล (30 วันย้อนหลัง)
        cutoff_date = datetime.now(THAILAND_TZ).date() - timedelta(days=30)
        
        # สั่งทำงาน Cleanup
        run_daily_cleanup(cutoff_date)
        
        # อัปเดต State ว่าวันนี้ได้ลบข้อมูลแล้ว
        st.session_state.last_cleanup_date = today_str
    # -----------------------------------------------------------------

    # --- 3.2 โหลดข้อมูล ---
    df = load_data() # 💥 FIX: โหลดจาก SQL


    # --- Layout หลัก ---
    main_col1, main_col2 = st.columns([1, 2])

    with main_col1:
        st.title("ระบบบันทึกเวลากิจกรรม")
        
        if st.session_state.last_message:
            msg_type, msg_content = st.session_state.last_message
            if msg_type == "success": st.success(msg_content)
            elif msg_type == "warning": st.warning(msg_content)
            elif msg_type == "error": st.error(msg_content)
            st.session_state.last_message = None 
        
        st.subheader("บันทึกกิจกรรม")

        # 1. โหลดข้อมูล User ID สำหรับ Dropdown
        user_id_list = [""] + sorted(load_user_data()) # "" (ว่าง) คือค่าเริ่มต้น
        current_id_in_state = st.session_state.get("current_emp_id", "")
        
        try:
            default_index = user_id_list.index(current_id_in_state)
        except ValueError:
            if current_id_in_state:
                user_id_list.append(current_id_in_state)
                default_index = len(user_id_list) - 1
            else:
                default_index = 0

        # 2. สร้าง SelectBox (Dropdown)
        selected_id = st.selectbox(
            "เลือก ID พนักงาน (หรือสแกน QR Code ด้านล่าง):",
            options=user_id_list,
            index=default_index,
            key="selectbox_emp_id"
        )

        # 3. Sync Logic (SelectBox)
        if selected_id != st.session_state.current_emp_id:
            st.session_state["current_emp_id"] = selected_id
            st.rerun() 
            
        emp_id_input = st.session_state.current_emp_id
            
        # 4. ส่วน Form สำหรับปุ่มกิจกรรม
        with st.form("activity_form", clear_on_submit=True): 
            
            if emp_id_input:
                st.info(f"ID ที่ใช้บันทึก: **{emp_id_input}**")
            else:
                st.info("กรุณาสแกนหรือเลือก ID พนักงานก่อนทำกิจกรรม")

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

        # 5. กล้องสแกน QR Code (อยู่ด้านล่างสุด)
        st.write("---") 
        st.write("สแกน QR/Barcode:ด้วยกล้อง")
        
        scanned_id = qrcode_scanner(key="qrcode_scanner_key_new")
        
        if scanned_id and scanned_id != st.session_state.current_emp_id:
            st.session_state["current_emp_id"] = scanned_id
            st.rerun() 
        st.write("---") 

    # -----------------------------------------------------------------
    # ส่วนคอลัมน์ขวา (แสดงข้อมูล)
    # -----------------------------------------------------------------
    with main_col2:
        st.markdown("---")
        st.subheader("ข้อมูลลงเวลา")

        col_filter1, col_filter2, col_filter3 = st.columns(3)
        filter_date_from = col_filter1.date_input("กรองตามวันที่ (From)", value=datetime.now().date(), key="date_from_key")
        filter_date_to = col_filter2.date_input("กรองตามวันที่ (To)", value=datetime.now().date(), key="date_to_key")
        
        unique_ids = ["All"] + sorted(load_user_data())
        filter_id = col_filter3.selectbox("กรองตาม Employee ID", options=unique_ids, key="id_filter_key")

        if df.empty:
            st.info("ยังไม่มีข้อมูลการลงเวลา")
        else:
            display_df = df.copy()
            display_df['Date_Obj'] = pd.to_datetime(display_df['date']).dt.date

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
                display_df = display_df[display_df['employee_id'] == filter_id] 

            if display_df.empty:
                st.info("ไม่พบข้อมูลการลงเวลาตามตัวกรองที่เลือก")
            else:
                display_df = display_df.drop(columns=['Date_Obj'], errors='ignore')
                display_df = display_df.reset_index(drop=True) 

                col_ratios = [0.5, 1, 1, 1.2, 1, 1, 1.3]
                cols = st.columns(col_ratios)
                headers = ["ลบ", "Employee ID", "Date", "ประเภทกิจกรรม", "เวลาเริ่ม", "เวลาสิ้นสุด", "**ระยะเวลา**"]
                for col, header in zip(cols, headers):
                    col.markdown(f"**{header}**")
                
                st.markdown('<hr style="margin: 0px 0px 0px 0px;">', unsafe_allow_html=True) 

                for index, row in display_df.iterrows(): 
                    original_index = row['Original_Index'] # นี่คือ 'id' จาก SQL
                    cols = st.columns(col_ratios)
                    time_style = "class='time-display'"
                    
                    if cols[0].button("❌", key=f"del_{original_index}_{index}", on_click=delete_log_entry, args=(original_index,), help="ลบ Log ลงเวลานี้"):
                         st.rerun()
                    
                    cols[1].write(row['employee_id'])
                    cols[2].write(row['date'])
                    cols[3].write(row['activity_type'])
                    cols[4].markdown(f"<p {time_style}>{format_time_display(row['start_time'])}</p>", unsafe_allow_html=True)
                    end_time_display = format_time_display(row['end_time'])
                    cols[5].markdown(f"<p {time_style}>{end_time_display}</p>", unsafe_allow_html=True)
                    duration_display = format_duration(row['duration_minutes'])
                    cols[6].markdown(f"<p {time_style}>{duration_display}</p>", unsafe_allow_html=True)
        
        st.subheader("ดาวน์โหลดข้อมูล")

        csv_data = get_csv_content_with_bom(df) 

        if csv_data:
            st.download_button(
                label="Download Log File (.csv)",
                data=csv_data,
                file_name="time_logs_export.csv",
                mime="text/csv",
                key="download_button_key"
            )

# -----------------------------------------------------------------
if __name__ == "__main__":
    main()
