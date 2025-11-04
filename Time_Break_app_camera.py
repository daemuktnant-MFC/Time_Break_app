# -----------------------------------------------------------------
# 💥 NEW: ฟังก์ชัน MAIN (ฉบับแก้ไข)
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
    
    # 💥 [FIX] แก้ไขการตั้งค่าเริ่มต้นสำหรับ selectbox
    # เราจะตั้งค่านี้เฉพาะเมื่อ state ยังไม่มีอยู่จริงเท่านั้น
    if "selectbox_chooser" not in st.session_state:
        st.session_state["selectbox_chooser"] = "--- เลือก ID (ถ้ามี) ---"


    # --- 3.1 การเริ่มต้นไฟล์ข้อมูล ---
    initialize_data_file()

    # --- 3.2 โหลดข้อมูล ---
    df = load_data() 
    existing_ids = sorted(load_user_data()) # 💥 [NEW] โหลด ID ผู้ใช้


    # -----------------------------------------------------------------
    # --- Layout หลัก ---
    main_col1, main_col2 = st.columns([1, 2])

    with main_col1:
        st.title("ระบบบันทึกเวลา")
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
        #st.subheader("บันทึกกิจกรรม")

        # 💥 [MODIFIED] 1. Selectbox (ตัวเลือกเสริม)
        options = ["--- เลือก ID (ถ้ามี) ---"] + existing_ids 
        
        # 💥 [FIX] สร้าง Callback สำหรับ Selectbox
        def sync_from_selectbox():
            selected_val = st.session_state.selectbox_chooser
            if selected_val and selected_val != "--- เลือก ID (ถ้ามี) ---":
                st.session_state.manual_emp_id_input_outside_form = selected_val
                st.session_state.current_emp_id = selected_val
            # on_change จะ rerun ให้อัตโนมัติ

        # 💥 [FIX] สร้าง Callback สำหรับ Text Input
        def sync_from_text_input():
            typed_val = st.session_state.manual_emp_id_input_outside_form.strip()
            st.session_state.current_emp_id = typed_val
            
            # ซิงค์ค่ากลับไปที่ selectbox
            if typed_val in existing_ids:
                st.session_state.selectbox_chooser = typed_val
            else:
                st.session_state.selectbox_chooser = "--- เลือก ID (ถ้ามี) ---"
            # on_change จะ rerun ให้อัตโนมัติ

        st.selectbox(
            "หรือเลือก ID ที่มีอยู่:",
            options=options,
            key="selectbox_chooser",
            on_change=sync_from_selectbox,
            help="""เลือก ID จาก
    ที่นี่จะเติมค่าลงในช่อง 'กรอก ID' ด้านล่าง""" # 💥 [FIX] แก้ SyntaxError
        )

        # 💥 [MODIFIED] 2. กล่องกรอก ID ด้วยมือ (Manual Input)
        st.text_input(
            "กรอก ID ด้วยมือ:", 
            key="manual_emp_id_input_outside_form", 
            on_change=sync_from_text_input, # 💥 [FIX] เพิ่ม on_change
            placeholder="กรอก ID ที่นี่ หรือเลือกจากด้านบน"
        )

        # 💥 [REMOVED] ลบ Logic ที่ทำให้เกิด Error ออก
        # Logic: ถ้ามีการกรอก Manual Input ให้ค่านี้แทนที่ใน session_state 
        # (ส่วนนี้ถูกย้ายไปอยู่ใน on_change callback 'sync_from_text_input' แล้ว)
        
        emp_id_input = st.session_state.get("current_emp_id", "").strip()
        
        # -----------------------------------------------------------------
        # 💥 FIX: 3. ส่วน Form/ปุ่มกิจกรรม (เหมือนเดิม)
        # -----------------------------------------------------------------
        
        with st.form("activity_form", clear_on_submit=False): 
            
            if emp_id_input:
                st.info(f"ID ที่ใช้บันทึก: **{emp_id_input}**")
            else:
                st.info("กรุณาสแกน, เลือก หรือกรอก Employee ID ก่อนทำกิจกรรม")

            st.write("เลือกกิจกรรม:")
            
            activity_buttons_col1, activity_buttons_col2, activity_buttons_col3, activity_buttons_col4 = st.columns(4)

            is_disabled = not bool(emp_id_input) 
            
            # ปุ่มกิจกรรม (ใช้ on_click)
            submitted_Break = activity_buttons_col1.form_submit_button("เริ่มพักเบรค", type="primary", use_container_width=True, disabled=is_disabled,
                                                                    on_click=submit_activity, args=("Break",))
            submitted_smoking = activity_buttons_col2.form_submit_button("สูบบุหรี่", use_container_width=True, disabled=is_disabled,
                                                                       on_click=submit_activity, args=("Smoking",))
            submitted_toilet = activity_buttons_col3.form_submit_button("เข้าห้องน้ำ", use_container_width=True, disabled=is_disabled,
                                                                      on_click=submit_activity, args=("Toilet",))
            submitted_end_activity = activity_buttons_col4.form_submit_button("สิ้นสุดกิจกรรม", type="secondary", use_container_width=True, disabled=is_disabled,
                                                                           on_click=submit_activity, args=("End_Activity",))

        # -----------------------------------------------------------------
        # 💥 FIX: 4. กล้องสแกน QR Code
        # -----------------------------------------------------------------
        st.write("---") # เส้นคั่นก่อนส่วนสแกน
        st.write("หรือ สแกน QR/Barcode:")
        
        # 4. QR Code Scanner: Component ที่เปิดกล้อง
        scanned_id = qrcode_scanner(key="qrcode_scanner_key_new")
        
        # Logic: ถ้าสแกนได้ ให้บันทึกค่าลง session_state ทันที
        if scanned_id and scanned_id != st.session_state.get("current_emp_id", ""):
            st.session_state["current_emp_id"] = scanned_id
            st.session_state["manual_emp_id_input_outside_form"] = scanned_id # Sync ให้ input แสดงค่า
            
            # 💥 [MODIFIED] Sync ให้ selectbox แสดงค่าที่สแกน (ถ้ามี)
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
        st.subheader("ข้อมูลลงเวลา")

        # --- ส่วน Filter (เหมือนเดิม) ---
        col_filter1, col_filter2, col_filter3 = st.columns(3)

        filter_date_from = col_filter1.date_input("กรองตามวันที่ (From)", value=datetime.now().date(), key="date_from_key")
        filter_date_to = col_filter2.date_input("กรองตามวันที่ (To)", value=datetime.now().date(), key="date_to_key")

        unique_ids = ["All"] + existing_ids # 💥 [MODIFIED] ใช้ existing_ids ที่โหลดไว้แล้ว
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
# -----------------------------------------------------------------
# 💥 การเรียกใช้งานฟังก์ชันหลัก
# -----------------------------------------------------------------
if __name__ == "__main__":
    main()
