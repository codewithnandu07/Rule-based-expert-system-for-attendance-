import streamlit as st
from datetime import datetime
import pandas as pd
import io

st.set_page_config(page_title="Auto Attendance", layout="centered")
st.title("🤖 Auto Attendance with Voice")

# --- RULES ---
st.sidebar.header("📜 Rules")
on_time = st.sidebar.time_input("On-Time", datetime.strptime("09:10", "%H:%M").time())
late_limit = st.sidebar.time_input("Late Limit", datetime.strptime("09:30", "%H:%M").time())

if 'attendance' not in st.session_state:
    st.session_state.attendance = []
    st.session_state.late_count = {}
    st.session_state.last_voice = ""

# --- INPUTS ---
name = st.text_input("Student Name")
id_card = st.selectbox("ID Card Scanned?", ["Yes", "No"])
face_match = st.slider("Face Match %", 0, 100, 85)

photo = st.camera_input("📷 Take Photo - Will Auto Mark")

# --- AUTO ENGINE + VOICE ---
def speak(text):
    # This JS will speak on phone/laptop browser
    js = f"""
    <script>
    var msg = new SpeechSynthesisUtterance("{text}");
    window.speechSynthesis.speak(msg);
    </script>
    """
    st.components.v1.html(js, height=0)

if photo and name:
    now = datetime.now()
    entry_time = now.time()

    # Check duplicate today
    today = now.strftime("%d-%m-%Y")
    already = [r for r in st.session_state.attendance if r["Name"]==name and r["Date"]==today]

    if not already:
        # RULES
        if face_match < 50:
            status = "Proxy Suspected"
            rule = "Rule 7"
        elif entry_time <= on_time and id_card=="Yes" and face_match>=80:
            status = "Present"
            rule = "Rule 1"
        elif entry_time <= late_limit and id_card=="Yes":
            c = st.session_state.late_count.get(name, 0) + 1
            st.session_state.late_count[name] = c
            if c >= 3:
                status = "Absent"
                rule = "Rule 4: 3 Lates"
                st.session_state.late_count[name]=0
            else:
                status = f"Late ({c}/3)"
                rule = "Rule 2"
        else:
            status = "Absent"
            rule = "Rule 3"

        st.session_state.attendance.append({
            "Date": today,
            "Time": entry_time.strftime("%H:%M:%S"),
            "Name": name,
            "Status": status,
            "Rule": rule,
            "Face%": face_match
        })

        # VOICE
        voice_text = f"{name} marked as {status}"
        st.session_state.last_voice = voice_text
        speak(voice_text)

        if "Present" in status:
            st.success(f"✅ {voice_text}")
            st.balloons()
        elif "Late" in status:
            st.warning(f"⚠️ {voice_text}")
        else:
            st.error(f"❌ {voice_text}")
    else:
        st.warning(f"{name} already marked today")

# --- SHEET + EXCEL DOWNLOAD ---
if st.session_state.attendance:
    st.divider()
    st.subheader("📋 Live Attendance")
    df = pd.DataFrame(st.session_state.attendance)
    st.dataframe(df, use_container_width=True)

    # Defaulter
    st.subheader("🚨 Defaulter <75%")
    total = df.groupby('Name').size()
    present = df[df['Status']=='Present'].groupby('Name').size()
    for s in total.index:
        perc = (present.get(s,0)/total[s])*100
        if perc < 75:
            st.error(f"{s}: {perc:.1f}% Defaulter")

    # EXCEL DOWNLOAD
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)

    st.download_button(
        label="📥 Download Excel Sheet",
        data=output.getvalue(),
        file_name=f"attendance_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    if st.button("Clear All"):
        st.session_state.attendance = []
        st.rerun()

# Speak last status again if page refresh
if st.session_state.last_voice:
    if st.button(f"🔊 Replay Voice: {st.session_state.last_voice}"):
        speak(st.session_state.last_voice)
