import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np
import math

# --- CSS (ชุดเดิม) ---
CUSTOM_CSS = """
<style>
/* ... (CSS เดิมของคุณ) ... */
div.stButton > button[kind="secondaryFormSubmit"] {
    padding: 1px 5px !important;
    font-size: 10px !important;
    height: 22px !important;
    line-height: 1 !important;
}
.time-display {
    font-size: 1.1em;
    font-weight: bold;
    margin-top: -10px;
    margin-bottom: -10px;
}
</style>
"""

# --- 1. ฟังก์ชันจัดการฐานข้อมูล ---

# ฟังก์ชันสำหรับสร้างตาราง หากยังไม่มี
def initialize_database(conn):
    """
    สร้างตาราง 'time_logs' ถ้ายังไม่มี
    เราจะเพิ่มคอลัมน์ id เพื่อเป็น Primary Key
    """
    create_table_query = """
    CREATE TABLE IF NOT EXISTS time_logs (
        id SERIAL PRIMARY KEY,
        Employee_ID TEXT NOT NULL,
        Date DATE NOT NULL,
        Clock_In TIME NOT NULL,
        Clock_Out TIME,
        Break_Duration_Minutes INT DEFAULT 0,
        UNIQUE(Employee_ID, Date) 
    );
    """
    # conn.query() ใช้สำหรับรัน SQL ที่ไม่มีการคืนค่า (เช่น CREATE, INSERT, UPDATE, DELETE)
    conn.query(create_table_query)

# ฟังก์ชันสำหรับโหลดข้อมูลจาก DB
@st.cache_data(ttl=60) # Cache ข้อมูล 60 วินาที
def load_logs(_conn):
    """
    โหลดข้อมูลทั้งหมดจากตาราง 'time_logs'
    """
    # _conn.query() ใช้สำหรับรัน SQL ที่มีการคืนค่า (เช่น SELECT)
    # เราใช้ _conn (มีขีดล่าง) เพื่อบอก Streamlit ว่านี่คือ object ที่ต้อง cache
    df = _conn.query("SELECT * FROM time_logs ORDER BY Date DESC, Clock_In DESC", ttl=60)
    
    # แปลงประเภทข้อมูลให้ถูกต้อง (ถ้าจำเป็น)
    if not df.empty:
        df['Date'] = pd.to_datetime(df['date']).dt.date
    return df

# ฟังก์ชันสำหรับเพิ่ม Log (INSERT)
def add_log_entry(conn, employee_id, date, clock_in):
    """
    เพิ่ม Log ใหม่ลงในฐานข้อมูล
    ใช้ "ON CONFLICT" เพื่อป้องกันการลงเวลาซ้ำในวันเดียวกัน
    """
    insert_query = """
    INSERT INTO time_logs (Employee_ID, Date, Clock_In)
    VALUES (:emp_id, :date, :clock_in)
    ON CONFLICT (Employee_ID, Date) DO NOTHING;
    """
    try:
        conn.query(
            insert_query,
            params={"emp_id": employee_id, "date": date, "clock_in": clock_in}
        )
        st.cache_data.clear() # ล้าง cache เพื่อให้ load_logs ดึงข้อมูลใหม่
        return True
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
        return False

# ฟังก์ชันสำหรับอัปเดตเวลา Clock Out (UPDATE)
def update_clock_out(conn, log_id, clock_out_time):
    """
    อัปเดตเวลา Clock Out โดยใช้ 'id'
    """
    update_query = """
    UPDATE time_logs
    SET Clock_Out = :clock_out
    WHERE id = :log_id;
    """
    conn.query(
        update_query,
        params={"clock_out": clock_out_time, "log_id": log_id}
    )
    st.cache_data.clear()

# ฟังก์ชันสำหรับอัปเดตเวลาเบรค (UPDATE)
def update_break_duration(conn, log_id, break_duration):
    """
    อัปเดตเวลาเบรค (นาที) โดยใช้ 'id'
    """
    update_query = """
    UPDATE time_logs
    SET Break_Duration_Minutes = :break
    WHERE id = :log_id;
    """
    conn.query(
        update_query,
        params={"break": break_duration, "log_id": log_id}
    )
    st.cache_data.clear()

# ฟังก์ชันสำหรับลบ Log (DELETE)
def delete_log_entry(conn, log_id):
    """
    ลบ Log โดยใช้ 'id'
    """
    delete_query = "DELETE FROM time_logs WHERE id = :log_id;"
    conn.query(delete_query, params={"log_id": log_id})
    st.cache_data.clear()

# --- 2. ฟังก์ชันคำนวณและแสดงผล (ชุดเดิม) ---

def format_time_display(time_obj):
    if pd.isnull(time_obj) or time_obj is None:
        return "N/A"
    try:
        # ถ้าเป็น string อยู่แล้ว (เช่น '10:30:00')
        if isinstance(time_obj, str):
            return datetime.strptime(time_obj, '%H:%M:%S').strftime('%H:%M')
        # ถ้าเป็น object ของ datetime.time
        return time_obj.strftime('%H:%M')
    except (ValueError, TypeError):
        return "Error"

def format_break_duration(minutes):
    if pd.isnull(minutes) or minutes == 0:
        return "00:00"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"

# --- 3. ส่วนหน้าเว็บ (UI) ---

st.set_page_config(page_title="Time Logger", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
st.title("ระบบบันทึกเวลา (เชื่อมต่อฐานข้อมูล)")

# --- 3.1 เชื่อมต่อฐานข้อมูล ---
try:
    # "mydb" คือชื่อ Connection ที่เราตั้งใน secrets.toml
    conn = st.connection("mydb", type="sql")
except Exception as e:
    st.error("ไม่สามารถเชื่อมต่อฐานข้อมูลได้ กรุณาตรวจสอบไฟล์ secrets.toml")
    st.error(e)
    st.stop() # หยุดการทำงานหากเชื่อมต่อไม่ได้

# --- 3.2 สร้างตาราง (ถ้ายังไม่มี) ---
initialize_database(conn)

# --- 3.3 โหลดข้อมูล ---
df = load_logs(conn)

# --- 3.4 ส่วนรับ Input (Sidebar) ---
st.sidebar.header("บันทึกเวลา")
emp_id_input = st.sidebar.text_input("Employee ID")
date_input = st.sidebar.date_input("Date", datetime.now())
clock_in_input = st.sidebar.time_input("Clock In", datetime.now().time())

if st.sidebar.button("บันทึก Clock In", type="primary"):
    if emp_id_input:
        if add_log_entry(conn, emp_id_input, date_input, clock_in_input):
            st.sidebar.success(f"บันทึกเวลาสำหรับ ID: {emp_id_input} เรียบร้อย!")
            # Rerun เพื่ออัปเดตตารางทันที
            st.rerun()
        else:
            st.sidebar.error("ไม่สามารถบันทึกได้ (อาจมีข้อมูลวันนี้อยู่แล้ว)")
    else:
        st.sidebar.warning("กรุณาใส่ Employee ID")

# --- 3.5 ส่วนแสดงผลข้อมูล (หน้าหลัก) ---
st.header("Time Logs")

# --- ส่วน Filter (ถ้าต้องการ) ---
st.subheader("Filter")
col_filter1, col_filter2 = st.columns(2)
filter_date = col_filter1.date_input("กรองตามวันที่", value=None)
unique_ids = ["All"] + sorted(df['employee_id'].unique())
filter_id = col_filter2.selectbox("กรองตาม Employee ID", options=unique_ids)

# --- สร้างตารางแสดงผล (ใช้ st.columns) ---
if df.empty:
    st.info("ยังไม่มีข้อมูลการลงเวลา")
else:
    # กรองข้อมูล
    display_df = df.copy()
    if filter_date:
        display_df = display_df[display_df['Date'] == filter_date]
    if filter_id != "All":
        display_df = display_df[display_df['employee_id'] == filter_id]

    # --- ส่วนหัวตาราง ---
    col_ratios = [0.5, 1, 1, 1, 1, 1, 1] # เพิ่มคอลัมน์สำหรับ ID
    cols = st.columns(col_ratios)
    headers = ["ลบ", "Log ID", "Employee ID", "Date", "Clock In", "Clock Out", "รวมเวลาเบรค"]
    for col, header in zip(cols, headers):
        col.markdown(f"**{header}**")
    st.markdown("---")

    # --- วนลูปแสดงข้อมูล ---
    for _, row in display_df.iterrows():
        # 'id' คือ Primary Key จากฐานข้อมูล
        log_id = row['id'] 
        
        cols = st.columns(col_ratios)
        
        # คอลัมน์ที่ 1: ปุ่มลบ
        cols[0].button(
            "❌",
            key=f"del_{log_id}",
            on_click=delete_log_entry,
            args=(conn, log_id), # ส่ง conn และ log_id
            help="ลบ Log ลงเวลานี้"
        )
        
        # คอลัมน์ที่ 2 - 4: ข้อมูลมาตรฐาน
        cols[1].write(log_id)
        cols[2].write(row['employee_id'])
        cols[3].write(row['Date'].strftime('%Y-%m-%d'))
        cols[4].markdown(f"<p class='time-display'>{format_time_display(row['clock_in'])}</p>", unsafe_allow_html=True)

        # คอลัมน์ที่ 5: Clock Out
        if pd.isnull(row['clock_out']):
            if cols[5].button("Clock Out", key=f"cout_{log_id}", type="primary"):
                update_clock_out(conn, log_id, datetime.now().time())
                st.rerun()
        else:
            cols[5].markdown(f"<p class='time-display'>{format_time_display(row['clock_out'])}</p>", unsafe_allow_html=True)
            if cols[5].button("แก้ไข", key=f"edit_cout_{log_id}"):
                # (Optional: สร้าง logic การแก้ไขเวลา)
                pass 

        # คอลัมน์ที่ 6: เวลาเบรค
        current_break_min = row['break_duration_minutes']
        break_display = format_break_duration(current_break_min)
        cols[6].markdown(f"<p class='time-display'>{break_display}</p>", unsafe_allow_html=True)
        
        # ปุ่มเพิ่ม/ลด เวลาเบรค
        btn_cols = cols[6].columns(2)
        if btn_cols[0].button("➕ 15m", key=f"add_break_{log_id}"):
            update_break_duration(conn, log_id, current_break_min + 15)
            st.rerun()
        if btn_cols[1].button("➖ 15m", key=f"sub_break_{log_id}"):
            new_break = max(0, current_break_min - 15) # กันไม่ให้ติดลบ
            update_break_duration(conn, log_id, new_break)
            st.rerun()

    st.markdown("---")

# (Optional) ส่วนแสดงข้อมูลดิบ
with st.expander("ดูข้อมูลดิบ (Raw Data from Database)"):
    st.dataframe(df)
