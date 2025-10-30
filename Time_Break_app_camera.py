import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timezone, timedelta # เพิ่ม time
import os
import numpy as np
import math
import pathlib
import base64
# 💥 NEW: Import สำหรับการสแกน QR Code
from streamlit_qrcode_scanner import qrcode_scanner # ต้องมีบรรทัดนี้ด้านบนสุดของไฟล์

# -----------------------------------------------------------------
# กำหนดเส้นทางไฟล์ให้ชี้ไปที่ Desktop (เหมือนเดิม)
# -----------------------------------------------------------------
LOGS_DIR = os.path.join(os.path.expanduser('~'), 'Desktop', 'TimeLogs')
DATA_FILE = os.path.join(LOGS_DIR, "time_logs.csv")

# -----------------------------------------------------------------
# 💥 แก้ไข: ชื่อคอลัมน์ใหม่
# -----------------------------------------------------------------
CSV_COLUMNS = ['Employee_ID', 'Date', 'Start_Time', 'End_Time', 'Activity_Type', 'Duration_Minutes']

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

# -----------------------------------------------------------------
# 💥 NEW: ฟังก์ชัน MAIN (ปรับปรุง Layout แก้ไขช่องว่าง)
# -----------------------------------------------------------------
def main():
    # --- 3. ส่วนหน้าเว็บ (UI) ---
    st.set_page_config(page_title="Time Logger", layout="wide")

    # (ส่วน Session State... เหมือนเดิม)
    if "current_emp_id" not in st.session_state:
        st.session_state["current_emp_id"] = ""
    if "manual_emp_id_input" not in st.session_state:
        st.session_state["manual_emp_id_input"] = ""
    if "last_message" not in st.session_state:
        st.session_state.last_message = None

    # --- 3.1 การเริ่มต้นไฟล์ข้อมูล ---
    initialize_data_file()

    # --- 3.2 โหลดข้อมูล ---
    df = load_data() 

    # --- 3.3 Callback Function ---
    # (ฟังก์ชัน submit_activity(...) เหมือนเดิมทุกประการ)
    def submit_activity(activity_type):
        """
        Callback ที่จะทำงานเมื่อกดปุ่ม
        ฟังก์ชันนี้จะทำงาน 'ก่อน' ที่หน้าเว็บจะ Rerun
        """
        
        # 1. ดึง ID จาก session_state (ที่ถูกตั้งค่าโดย sync logic)
        emp_id = st.session_state.get("current_emp_id", "")
        if not emp_id:
            st.session_state.last_message = ("warning", "กรุณาสแกนหรือกรอก Employee ID ก่อนทำกิจกรรม")
            return # หยุดทำงานถ้าไม่มี ID

        # 2. ดึงเวลาปัจจุบัน
        THAILAND_TZ = timezone(timedelta(hours=7))
        now_thailand = datetime.now(THAILAND_TZ)
        current_date_str = now_thailand.date().strftime('%Y-%m-%d')
        current_time_str = now_thailand.time().strftime('%H:%M:%S')

        # 3. Logic การบันทึก (ย้ายมาจากใน Form)
        if activity_type == "End_Activity":
            if clock_out_latest_activity(emp_id, current_date_str, current_time_str):
                # 4. ตั้งค่า Message และล้างค่า
                st.session_state.last_message = ("success", f"✅ สิ้นสุดกิจกรรมล่าสุด สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อย!")
                st.session_state["current_emp_id"] = "" 
                st.session_state["manual_emp_id_input"] = "" # ล้างค่าได้เพราะยังไม่ rerender
            else:
                st.session_state.last_message = ("warning", f"⚠️ ไม่พบกิจกรรมที่กำลังดำเนินอยู่สำหรับ ID: **{emp_id}** วันที่ {current_date_str}")
        else:
            # (activity_type คือ "Break", "Smoking", "Toilet")
            if log_activity_start(emp_id, current_date_str, current_time_str, activity_type):
                success_message = f"✅ เริ่มกิจกรรม **{activity_type}** สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อย!"
                if activity_type == "Smoking":
                    success_message = f"🚭 เริ่มสูบบุหรี่ สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อย!"
                elif activity_type == "Toilet":
                     success_message = f"🚻 เริ่มเข้าห้องน้ำ สำหรับ ID: **{emp_id}** เวลา {current_time_str} เรียบร้อย!"
                
                # 4. ตั้งค่า Message และล้างค่า
                st.session_state.last_message = ("success", success_message)
                st.session_state["current_emp_id"] = "" 
                st.session_state["manual_emp_id_input"] = "" # ล้างค่าได้เพราะยังไม่ rerender
            else:
                st.session_state.last_message = ("error", f"เกิดข้อผิดพลาดในการเริ่มกิจกรรม {activity_type}")


    # สร้าง 2 คอลัมน์หลักสำหรับ Layout ทั้งหมด
    main_col1, main_col2 = st.columns([1, 2])
    
    # -----------------------------------------------------------------
    # ส่วนคอลัมน์ซ้าย
    # -----------------------------------------------------------------
    with main_col1:
        st.title("ระบบบันทึกเวลากิจกรรม")
        st.markdown(f"**บันทึกข้อมูลที่:** `{LOGS_DIR}`")

        # (ส่วนแสดง Message... เหมือนเดิม)
        if st.session_state.last_message:
            msg_type, msg_content = st.session_state.last_message
            if msg_type == "success":
                st.success(msg_content)
            elif msg_type == "warning":
                st.warning(msg_content)
            elif msg_type == "error":
                st.error(msg_content)
            st.session_state.last_message = None 

        # --- ส่วน Input ID (Manual/QR) ---
        
        # 1. ย้าย QR Scanner ขึ้นมาก่อน (เหมือนเดิม)
        st.markdown("หรือ สแกน QR/Barcode:") 
        scanned_id = qrcode_scanner(key="qrcode_scanner_key_new")

        # ---------------------------------------------------------
        # 💥💥💥 FIX: 2. เพิ่มเงื่อนไขป้องกัน Loop 💥💥💥
        # ---------------------------------------------------------
        
        # Rerun ต่อเมื่อ:
        # 1. มีการสแกน (scanned_id is not None)
        # 2. ค่าที่สแกน 'ไม่ตรงกับ' ค่าที่มีอยู่แล้วใน session_state
        if scanned_id and scanned_id != st.session_state.manual_emp_id_input:
            st.session_state["manual_emp_id_input"] = scanned_id # Update state
            st.session_state["current_emp_id"] = scanned_id      # Update state
            st.rerun() # Rerun แค่ครั้งเดียว
        
        # 3. วาด Manual Input ทีหลัง (เหมือนเดิม)
        manual_input = st.text_input(
            "กรอก ID ด้วยมือ (ถ้าสแกนไม่ได้):", 
            key="manual_emp_id_input", 
            placeholder="กรอก ID ที่นี่"
        )
        
        # 4. Sync Logic ส่วนที่เหลือ (เหมือนเดิม)
        if manual_input != st.session_state.get("current_emp_id", ""):
             st.session_state["current_emp_id"] = manual_input
        else:
             st.session_state["current_emp_id"] = st.session_state["manual_emp_id_input"]

        
        emp_id_input = st.session_state.get("current_emp_id", "")
            
        # --- ส่วนปุ่ม Button + on_click --- (เหมือนเดิม)
        if emp_id_input:
            st.info(f"ID ที่ใช้บันทึก: **{emp_id_input}**")
        else:
            st.info("กรุณาสแกนหรือกรอก Employee ID ก่อนทำกิจกรรม") 

        st.write("เลือกกิจกรรม:")
        
        activity_buttons_col1, activity_buttons_col2, activity_buttons_col3, activity_buttons_col4 = st.columns(4)

        is_disabled = not bool(emp_id_input) 
        
        with activity_buttons_col1:
            st.button("เริ่มพักเบรค", type="primary", use_container_width=True, disabled=is_disabled,
                        on_click=submit_activity, args=("Break",))
        
        with activity_buttons_col2:
            st.button("สูบบุหรี่", use_container_width=True, disabled=is_disabled,
                        on_click=submit_activity, args=("Smoking",))
        
        with activity_buttons_col3:
            st.button("เข้าห้องน้ำ", use_container_width=True, disabled=is_disabled,
                        on_click=submit_activity, args=("Toilet",))
        
        with activity_buttons_col4:
            st.button("สิ้นสุดกิจกรรม", type="secondary", use_container_width=True, disabled=is_disabled,
                        on_click=submit_activity, args=("End_Activity",))

        # (ส่วน Download... เหมือนเดิม)
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

        st.markdown("---") 

    # -----------------------------------------------------------------
    # ส่วนคอลัมน์ขวา (เหมือนเดิมทุกประการ)
    # -----------------------------------------------------------------
    with main_col2:
        # (โค้ดทั้งหมดใน main_col2 เหมือนเดิม)
        st.subheader("ข้อมูลลงเวลา")

        # --- ส่วน Filter ---
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        filter_date_from = col_filter1.date_input("กรองตามวันที่ (From)", value=datetime.now().date(), key="date_from_key")
        filter_date_to = col_filter2.date_input("กรองตามวันที่ (To)", value=datetime.now().date(), key="date_to_key")
        unique_ids = ["All"]
        if not df.empty and 'Employee_ID' in df.columns:
            unique_ids += sorted(df['Employee_ID'].dropna().unique())
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
                
                st.markdown("---") 

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
if __name__ == "__main__":
    main()
