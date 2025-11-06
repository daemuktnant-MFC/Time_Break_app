import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timezone, timedelta
import numpy as np
import math
from streamlit.connections import SQLConnection
from streamlit_qrcode_scanner import qrcode_scanner
from sqlalchemy import text # 💥 [FIX 1/5] เพิ่มการ import นี้

# -----------------------------------------------------------------
# 💥 [MODIFIED] ชื่อคอลัมน์ใน DB (id คือ PK ที่เพิ่มมา)
DB_COLUMNS = ['id', 'Employee_ID', 'Date', 'Start_Time', 'End_Time', 'Activity_Type', 'Duration_Minutes']


# --- CSS (CLEANED) ---
CUSTOM_CSS = """
<style>
/* 1. FIX: ลดพื้นที่ว่างด้านบนสุด */
div.block-container {
    padding-top: 3rem; /* ลดพื้นที่ว่างด้านบน */
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
</style>
"""

# --- 1. ฟังก์ชันจัดการข้อมูล (แก้ไขทั้งหมด) ---

@st.cache_data(ttl=600) # Cache ข้อมูล 10 นาที
def load_data():
    """ 💥 [MODIFIED] โหลดข้อมูลจาก Supabase """
    try:
        conn = st.connection("supabase", type=SQLConnection)
        # เลือก "id" มาด้วย เพื่อใช้ในการลบ
        df = conn.query('SELECT id, "Employee_ID", "Date", "Start_Time", "End_Time", "Activity_Type", "Duration_Minutes" FROM time_logs ORDER BY "Date" DESC, "Start_Time" DESC;',
                        ttl=60) # Cache query 1 นาที

        if df.empty:
            return pd.DataFrame(columns=DB_COLUMNS)

        # -----------------------------------------------------------------
        # 💥 [FIX] แก้ไขการแปลงประเภทข้อมูลที่นี่
        # -----------------------------------------------------------------
        
        # 1. 'Date' (ประเภท date) - อันนี้ถูกต้องแล้ว
        df['Date'] = pd.to_datetime(df['Date']).dt.date.astype(str)
        
        # 2. 'Start_Time' (ประเภท time)
        # ถูกอ่านค่ามาเป็น datetime.time object
        # เราไม่สามารถใช้ pd.to_datetime() กับมันได้ ต้อง .apply(strftime) เลย
        df['Start_Time'] = df['Start_Time'].apply(
            lambda x: x.strftime('%H:%M:%S') if isinstance(x, time) else str(x)
        )

        # 3. 'End_Time' (ประเภท time และมีค่า NULL)
        # ใช้วิธีเดียวกับ Start_Time แต่เช็คค่าที่เป็น NULL (NaT/None) ด้วย
        df['End_Time'] = df['End_Time'].apply(
            lambda x: x.strftime('%H:%M:%S') if isinstance(x, time) else np.nan
        )
        # -----------------------------------------------------------------

        df['Duration_Minutes'] = pd.to_numeric(df['Duration_Minutes'], errors='coerce')

        return df

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลจาก Supabase: {e}")
        return pd.DataFrame(columns=DB_COLUMNS)

# -----------------------------------------------------------------
# 💥 [MODIFIED] ฟังก์ชันสำหรับจัดการ User Data (ID ที่ไม่ซ้ำ)
# -----------------------------------------------------------------

@st.cache_data(ttl=600)
def load_user_data():
    """ 💥 [MODIFIED] โหลดข้อมูล ID และ ชื่อ พนักงานจาก Supabase """
    # 💥 [FIX] แก้ไขการย่อหน้า (Indent) ทั้งหมดในฟังก์ชันนี้
    try:
        conn = st.connection("supabase", type=SQLConnection)
        
        # 💥 [FIX] เลือก "Employee_Name" มาด้วย (ต้องสร้างคอลัมน์นี้ใน Supabase ก่อน)
        sql_query = 'SELECT "Employee_ID", "Employee_Name" FROM user_data;'
        df_users = conn.query(sql_query, ttl=60)
        
        if df_users.empty:
            # 💥 [FIX] คืนค่าเป็น DataFrame ที่มี 2 คอลัมน์
            return pd.DataFrame(columns=["Employee_ID", "Employee_Name"])
            
        df_users['Employee_ID'] = df_users['Employee_ID'].astype(str)
        # 💥 [FIX] เติมค่าว่างสำหรับคนที่ยังไม่ได้กรอกชื่อ
        df_users['Employee_Name'] = df_users['Employee_Name'].astype(str).fillna("N/A") 
        
        return df_users.drop_duplicates(subset=['Employee_ID']) # กัน ID ซ้ำ

    except Exception as e:
        # 💥 [FIX] ตรวจสอบว่า Error เกิดเพราะไม่มีคอลัมน์ Employee_Name หรือไม่
        if 'column "Employee_Name" does not exist' in str(e):
             st.error("⚠️ [Error] ไม่พบคอลัมน์ 'Employee_Name' ในตาราง 'user_data'!")
             st.info("กรุณาเพิ่มคอลัมน์ 'Employee_Name' (type: text) ใน Supabase ก่อนครับ")
        else:
            st.warning(f"ไม่สามารถโหลด User List (ID/Name): {e}")
        
        # 💥 [FIX] คืนค่าเป็น DataFrame ว่าง
        return pd.DataFrame(columns=["Employee_ID", "Employee_Name"])

def save_unique_user_id(employee_id):
    """ 💥 [MODIFIED] บันทึก ID พนักงานใหม่ที่ไม่ซ้ำลงใน Supabase """
    employee_id = str(employee_id)
    if not employee_id:
        return

    try:
        conn = st.connection("supabase", type=SQLConnection)
        
        # 💥 [FIX 2/5] เปลี่ยนจาก conn.execute() เป็น conn.session.execute()
        with conn.session as s:
            s.execute(
                text('INSERT INTO user_data ("Employee_ID") VALUES (:Employee_ID) ON CONFLICT ("Employee_ID") DO NOTHING;'),
                params=[{"Employee_ID": employee_id}]
            )
            s.commit()
            
        st.cache_data.clear() # ล้าง cache ของ load_user_data
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึก User ID: {e}")

# 💥 [NO CHANGE] ฟังก์ชันคำนวณ Duration (เหมือนเดิม)
def calculate_duration(start_time_str, end_time_str):
    """คำนวณระยะเวลาเป็นนาที"""
    try:
        if pd.isnull(start_time_str) or pd.isnull(end_time_str) or str(start_time_str).lower() == 'nan' or str(end_time_str).lower() == 'nan':
            return np.nan

        # ตรวจสอบ format (HH:MM:SS หรือ HH:MM)
        time_formats = ['%H:%M:%S', '%H:%M']
        t_start_time = None
        t_end_time = None
        
        for fmt in time_formats:
            try:
                t_start_time = datetime.strptime(str(start_time_str), fmt).time()
                break
            except ValueError:
                continue
        
        for fmt in time_formats:
            try:
                t_end_time = datetime.strptime(str(end_time_str), fmt).time()
                break
            except ValueError:
                continue

        if t_start_time is None or t_end_time is None:
            return np.nan

        base_date = datetime(2000, 1, 1)
        t_start = datetime.combine(base_date, t_start_time)
        t_end = datetime.combine(base_date, t_end_time)

        if t_end < t_start:
            t_end += pd.Timedelta(days=1)

        duration_minutes = (t_end - t_start).total_seconds() / 60
        return max(0, duration_minutes)
    except (ValueError, TypeError, AttributeError):
        return np.nan

# 💥 [MODIFIED] ฟังก์ชัน Clock Out กิจกรรมล่าสุด
def clock_out_latest_activity(employee_id, date_str, end_time_str):
    """ค้นหาและ Clock Out กิจกรรมล่าสุดที่ยังเปิดอยู่ใน Supabase"""
    try:
        conn = st.connection("supabase", type=SQLConnection)
        
        # 1. ค้นหา 'id' ของแถวล่าสุดที่ยังไม่ปิด
        sql_find = """
        SELECT id FROM time_logs 
        WHERE "Employee_ID" = :Employee_ID AND "Date" = :Date AND "End_Time" IS NULL 
        ORDER BY "Start_Time" DESC 
        LIMIT 1;
        """
        result_df = conn.query(sql_find, params=[{"Employee_ID": employee_id, "Date": date_str}])
        
        if not result_df.empty:
            log_id_to_update = result_df['id'].iloc[0]
            
            # 2. ดึง Start_Time มาคำนวณ
            start_time_df = conn.query('SELECT "Start_Time" FROM time_logs WHERE id = :id;',params=[{"id": int(log_id_to_update)}])
            
            # -----------------------------------------------------------------
            # 💥 [FIX] แก้ไขจุดนี้: conn.query() คืนค่า object datetime.time
            # เราจึงไม่สามารถใช้ pd.to_datetime() กับมันได้
            # ให้เราดึง object .iloc[0] แล้ว .strftime() โดยตรง
            start_time_obj = start_time_df['Start_Time'].iloc[0]
            start_time = start_time_obj.strftime('%H:%M:%S')
            # -----------------------------------------------------------------

            duration = calculate_duration(start_time, end_time_str)
            
            # 3. อัปเดตแถวนั้น
            sql_update = """
            UPDATE time_logs 
            SET "End_Time" = :End_Time, "Duration_Minutes" = :Duration_Minutes 
            WHERE id = :id;
            """
            
            # (ส่วนนี้ถูกต้องแล้วจากครั้งก่อน)
            with conn.session as s:
                s.execute(
                    text(sql_update),
                    params=[{
                        "End_Time": end_time_str,
                        "Duration_Minutes": duration,
                        "id": int(log_id_to_update)
                    }]
                )
                s.commit()

            
            st.cache_data.clear() # ล้าง cache ของ load_data
            return True
            
    except Exception as e:
        st.warning(f"Internal Clock-out Error for ID {employee_id}: {e}")
        raise
    return False

# 💥 [MODIFIED] ฟังก์ชันเริ่มพักเบรคใหม่
def log_activity_start(employee_id, date_str, start_time_str, activity_type):
    """บันทึกการเริ่มพักเบรคใหม่ลง Supabase และ Clock Out กิจกรรมเดิม (ถ้ามี)"""
    try:
        # 1. Clock out กิจกรรมเดิมก่อน
        clock_out_latest_activity(employee_id, date_str, start_time_str) 
        
        # 2. เพิ่มแถวใหม่
        conn = st.connection("supabase", type=SQLConnection)
        
        sql_insert = """
        INSERT INTO time_logs 
        ("Employee_ID", "Date", "Start_Time", "End_Time", "Activity_Type", "Duration_Minutes") 
        VALUES (:Employee_ID, :Date, :Start_Time, :End_Time, :Activity_Type, :Duration_Minutes);
        """
        
        # 💥 [FIX 4/5] เปลี่ยนจาก conn.execute() เป็น conn.session.execute()
        with conn.session as s:
            s.execute(
                text(sql_insert),
                params=[{
                    "Employee_ID": employee_id,
                    "Date": date_str,
                    "Start_Time": start_time_str,
                    "End_Time": None,
                    "Activity_Type": activity_type,
                    "Duration_Minutes": None
                }]
            )
            s.commit()
        
        # 3. บันทึก ID ผู้ใช้
        save_unique_user_id(employee_id)
        
        st.cache_data.clear() # ล้าง cache ของ load_data
        return True
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเริ่มพักเบรค {activity_type}: {e}")
        return False

# 💥 [MODIFIED] ฟังก์ชันลบ
def delete_log_entry(log_id):
    """ลบ Log ตาม 'id' จาก Supabase"""
    try:
        conn = st.connection("supabase", type=SQLConnection)
        
        # 💥 [FIX 5/5] เปลี่ยนจาก conn.execute() เป็น conn.session.execute()
        with conn.session as s:
            s.execute(
                text('DELETE FROM time_logs WHERE id = :id;'),
                params=[{"id": int(log_id)}]
            )
            s.commit()
            
        st.cache_data.clear() # ล้าง cache ของ load_data
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการลบ Log ID {log_id}: {e}")

# --- 2. ฟังก์ชันคำนวณและแสดงผล (เหมือนเดิม) ---

def format_time_display(time_str):
    """จัดรูปแบบเวลาเป็น HH:MM"""
    if pd.isnull(time_str) or str(time_str).lower() == 'nan':
        return "N/A"
    try:
        # Supabase อาจคืนค่าเป็น HH:MM:SS.microseconds
        time_str = str(time_str).split('.')[0]
        return datetime.strptime(time_str, '%H:%M:%S').strftime('%H:%M')
    except (ValueError, TypeError):
        return str(time_str)

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


def get_csv_content_with_bom(df_to_download):
    """ 💥 [MODIFIED] สร้างลิงก์ดาวน์โหลด CSV จาก DataFrame พร้อม BOM """
    try:
        # ไม่ต้องอ่านไฟล์แล้ว ใช้ DataFrame ที่ส่งเข้ามาได้เลย
        csv_content = df_to_download.to_csv(index=False, encoding='utf-8-sig')
        bom = "\ufeff"
        content_with_bom = bom + csv_content
        return content_with_bom
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการสร้างไฟล์ CSV: {e}")
        return None


# -----------------------------------------------------------------
# 💥 [NO CHANGE] ฟังก์ชัน Callback submit_activity (เหมือนเดิม)
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
    current_time_str = now_thailand.time().strftime('%H:%M:%S') # ใช้ Format H:M:S

    # 3. Logic การบันทึก
    if activity_type == "End_Activity":
        if clock_out_latest_activity(emp_id, current_date_str, current_time_str):
            # 4. ตั้งค่า Message และล้างค่า
            st.session_state.last_message = ("success", f"✅ สิ้นสุดกิจกรรมล่าสุด สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อยแล้ว!")
            st.session_state["current_emp_id"] = "" 
            st.session_state["manual_emp_id_input_outside_form"] = "" 
            st.session_state["selectbox_chooser"] = "ค้นหา ID" 
        else:
            st.session_state.last_message = ("warning", f"⚠️ ไม่พบกิจกรรมที่กำลังดำเนินอยู่สำหรับ ID: **{emp_id}** วันที่ {current_date_str}")
            
    else:
        # (activity_type คือ "Break", "Smoking", "Toilet")
        if log_activity_start(emp_id, current_date_str, current_time_str, activity_type):
            success_message = f"✅ เริ่มพักเบรค **{activity_type}** สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อยแล้ว!"
            if activity_type == "Break":
                success_message = f"▶️ เริ่มงาน สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อยแล้ว!"
            elif activity_type == "Smoking":
                success_message = f"🚭 เริ่มสูบบุหรี่ สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อยแล้ว!"
            elif activity_type == "Toilet":
                success_message = f"🚻 เริ่มเข้าห้องน้ำ สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อยแล้ว!"
            
            # 4. ตั้งค่า Message และล้างค่า
            st.session_state.last_message = ("success", success_message)
            st.session_state["current_emp_id"] = "" 
            st.session_state["manual_emp_id_input_outside_form"] = "" 
            st.session_state["selectbox_chooser"] = "ค้นหา ID" 
        else:
            st.session_state.last_message = ("error", f"เกิดข้อผิดพลาดในการเริ่มพักเบรค {activity_type}")
            
    # 💥 [FIX] ลบ st.rerun() ที่ไม่จำเป็นออก (แก้ Warning: no-op)
    # on_click ใน form_submit_button จะ rerun ให้อัตโนมัติอยู่แล้ว
    # st.rerun() 


# -----------------------------------------------------------------
# 💥 [MODIFIED] ฟังก์ชัน MAIN
# -----------------------------------------------------------------
def main():
    # --- 3. ส่วนหน้าเว็บ (UI) ---
    st.set_page_config(page_title="Time Logger", layout="wide")
    
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Initialize Session State (เหมือนเดิม)
    if "current_emp_id" not in st.session_state:
        st.session_state["current_emp_id"] = ""
    if "manual_emp_id_input_outside_form" not in st.session_state: 
        st.session_state["manual_emp_id_input_outside_form"] = ""
    if "last_message" not in st.session_state:
        st.session_state.last_message = None
    if "selectbox_chooser" not in st.session_state:
        st.session_state["selectbox_chooser"] = "ค้นหา ID"

    # --- 3.2 โหลดข้อมูล ---
    df = load_data() # 💥 โหลด time_logs
    
    # 💥 [FIX] โหลด df_users (ที่มี ID และ Name)
    df_users = load_user_data() 
    
    # 💥 [FIX] สร้าง list ของ ID จาก df_users
    existing_ids = sorted(df_users['Employee_ID'].unique().tolist()) 

    # 💥 [FIX] Merge ข้อมูลชื่อพนักงาน (df_users) เข้ากับข้อมูลลงเวลา (df)
    if not df.empty and not df_users.empty:
        df = pd.merge(
            df, 
            df_users, 
            on="Employee_ID", 
            how="left" # ใช้ "left" เพื่อให้ log ยังแสดงแม้จะหาชื่อไม่พบ
        )
        # เติมค่าว่างสำหรับชื่อที่หาไม่เจอ (กรณี ID อยู่ใน time_logs แต่ไม่อยู่ใน user_data)
        df['Employee_Name'] = df['Employee_Name'].fillna("N/A")
    elif not df.empty:
        # ถ้า df_users ว่างเปล่า (โหลดไม่สำเร็จ) ให้สร้างคอลัมน์ชื่อว่างไว้
        df['Employee_Name'] = "N/A"


    # -----------------------------------------------------------------
    # --- Layout หลัก ---
    main_col1, main_col2 = st.columns([1, 2])

    with main_col1:
        st.title("ระบบบันทึกเวลา")
        st.success("💾 เชื่อมต่อฐานข้อมูล Supabase สำเร็จ")

        
        # ... (ส่วน Message, Selectbox, Text Input, Form, QR Code เหมือนเดิม) ...
        
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
        # 1. Selectbox (ตัวเลือกเสริม)
        options = ["ค้นหา ID"] + existing_ids 
        
        def sync_from_selectbox():
            selected_val = st.session_state.selectbox_chooser
            if selected_val and selected_val != "ค้นหา ID":
                st.session_state.manual_emp_id_input_outside_form = selected_val
                st.session_state.current_emp_id = selected_val

        def sync_from_text_input():
            typed_val = st.session_state.manual_emp_id_input_outside_form.strip()
            st.session_state.current_emp_id = typed_val
            
            if typed_val in existing_ids:
                st.session_state.selectbox_chooser = typed_val
            else:
                st.session_state.selectbox_chooser = "ค้นหา ID"

        st.selectbox(
            "หรือเลือก ID ที่มีอยู่:",
            options=options,
            key="selectbox_chooser",
            on_change=sync_from_selectbox,
            help="""เลือก ID จาก
    ที่นี่จะเติมค่าลงในช่อง 'กรอก ID' ด้านล่าง""" 
        )

        # 2. กล่องกรอก ID ด้วยมือ (Manual Input)
        st.text_input(
            "กรอก ID ด้วยมือ:", 
            key="manual_emp_id_input_outside_form", 
            on_change=sync_from_text_input, 
            placeholder="กรอก ID ที่นี่ หรือเลือกจากด้านบน"
        )
        
        emp_id_input = st.session_state.get("current_emp_id", "").strip()
        
        # -----------------------------------------------------------------
        # 3. ส่วน Form/ปุ่มกิจกรรม (เหมือนเดิม)
        # -----------------------------------------------------------------
        
        with st.form("activity_form", clear_on_submit=False): 
            
            if emp_id_input:
                # 💥 [FIX] แสดงชื่อพนักงาน (ถ้ามี)
                emp_name = "N/A"
                if not df_users.empty and emp_id_input in df_users['Employee_ID'].values:
                    emp_name = df_users[df_users['Employee_ID'] == emp_id_input]['Employee_Name'].iloc[0]

                if emp_name != "N/A":
                    st.info(f"ID: **{emp_id_input}** (คุณ: **{emp_name}**)")
                else:
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

        # -----------------------------------------------------------------
        # 4. กล้องสแกน QR Code (เหมือนเดิม)
        # -----------------------------------------------------------------
        st.write("---") 
        st.write("หรือ สแกน QR/Barcode:")
        
        scanned_id = qrcode_scanner(key="qrcode_scanner_key_new")
        
        if scanned_id and scanned_id != st.session_state.get("current_emp_id", ""):
            st.session_state["current_emp_id"] = scanned_id
            st.session_state["manual_emp_id_input_outside_form"] = scanned_id 
            
            if scanned_id in existing_ids:
                st.session_state["selectbox_chooser"] = scanned_id
            else:
                st.session_state["selectbox_chooser"] = "ค้นหา ID"
            
            st.rerun()


    # -----------------------------------------------------------------
    # ส่วนคอลัมน์ขวา (แสดงข้อมูล)
    # -----------------------------------------------------------------
    with main_col2:
        st.markdown("---")
        st.subheader("ข้อมูลลงเวลา")

        # --- ส่วน Filter (เหมือนเดิม) ---
        col_filter1, col_filter2, col_filter3 = st.columns(3)

        today = datetime.now().date()
        default_from_date = today - timedelta(days=30) 

        filter_date_from = col_filter1.date_input("กรองตามวันที่ (From)", value=default_from_date, key="date_from_key")
        filter_date_to = col_filter2.date_input("กรองตามวันที่ (To)", value=today, key="date_to_key")

        unique_ids = ["All"] + existing_ids 
        filter_id = col_filter3.selectbox("กรองตาม Employee ID", options=unique_ids, key="id_filter_key")


        # --- สร้างตารางแสดงผล ---
        if df.empty:
            st.info("ยังไม่มีข้อมูลการลงเวลา")
        else:
            # การกรอง (เหมือนเดิม)
            display_df = df.copy()
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
                display_df = display_df.reset_index(drop=True) 

                # 💥 [FIX] เพิ่มคอลัมน์ "ชื่อ-สกุล" และปรับสัดส่วน
                col_ratios = [0.5, 1, 1.5, 1, 1.2, 1, 1, 1.3] 
                cols = st.columns(col_ratios)
                headers = ["ลบ", "Employee ID", "ชื่อ-สกุล", "Date", "ประเภทกิจกรรม", "เวลาเริ่ม", "เวลาสิ้นสุด", "**ระยะเวลา**"]
                
                for col, header in zip(cols, headers):
                    col.markdown(f"**{header}**")
                
                st.markdown('<hr style="margin: 0px 0px 0px 0px;">', unsafe_allow_html=True) 

                for index, row in display_df.iterrows(): 
                    log_id = row['id'] 
                    cols = st.columns(col_ratios) # 💥 [FIX] ใช้ col_ratios ใหม่
                    time_style = "class='time-display'"
                    
                    if cols[0].button("❌", key=f"del_{log_id}_{index}", on_click=delete_log_entry, args=(log_id,), help="ลบ Log ลงเวลานี้"):
                         st.rerun()
                         
                    cols[1].write(row['Employee_ID'])
                    
                    # 💥 [FIX] แสดงชื่อ (cols[2])
                    cols[2].write(row.get('Employee_Name', 'N/A')) 
                    
                    # 💥 [FIX] เลื่อนคอลัมน์ที่เหลือ
                    cols[3].write(row['Date'])
                    cols[4].write(row['Activity_Type'])
                    cols[5].markdown(f"<p {time_style}>{format_time_display(row['Start_Time'])}</p>", unsafe_allow_html=True)
                    end_time_display = format_time_display(row['End_Time'])
                    cols[6].markdown(f"<p {time_style}>{end_time_display}</p>", unsafe_allow_html=True)
                    duration_display = format_duration(row['Duration_Minutes'])
                    cols[7].markdown(f"<p {time_style}>{duration_display}</p>", unsafe_allow_html=True)
        
        # -----------------------------------------------------------------
        # ส่วนสร้างปุ่มดาวน์โหลดไฟล์
        # -----------------------------------------------------------------
        st.subheader("ดาวน์โหลดข้อมูล")

        # 💥 [FIX] ตอนนี้ df ที่ดาวน์โหลดจะมีคอลัมน์ 'Employee_Name' 
        # (จากขั้นตอน Merge ด้านบน) ซึ่งถูกต้องแล้ว
        csv_data = get_csv_content_with_bom(df) 

        if csv_data:
            st.download_button(
                label="Download Log File (.csv)",
                data=csv_data,
                file_name=f"time_logs_{datetime.now().strftime('%Y%m%d')}.csv", 
                mime="text/csv",
                key="download_button_key"
            )

# -----------------------------------------------------------------
# 💥 การเรียกใช้งานฟังก์ชันหลัก
# -----------------------------------------------------------------
if __name__ == "__main__":
    main()








