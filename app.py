import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Attendance Expert System", layout="centered")
st.title("🧠 Rule-Based Attendance Expert System")
st.caption("Only Streamlit | No extra library needed")

# --- KNOWLEDGE BASE ---
st.sidebar.header("📜 Knowledge Base - Edit Rules")
on_time = st.sidebar.time_input("Rule 1: On-Time Limit", datetime.strptime("09:10", "%H:%M").time())
late_limit = st.sidebar.time_input("Rule 2: Late Limit", datetime.strptime("09:30", "%H:%M").time())
face_needed = st.sidebar.slider("Rule 1: Face Match Needed %", 0, 100, 80)
lates_for_absent = st.sidebar.number_input("Rule 4: Lates = 1 Absent", 1, 10, 3)

# Memory
if 'attendance' not in st.session_state:
    st.session_state.attendance = []
if 'late_count' not in st.session_state:
    st.session_state.late_count = {}

# --- FACT COLLECTION ---
st.subheader("📝 Enter Facts")
name = st.text_input("Student Name")
col1, col2 = st.columns(2)
with col1:
    entry_time = st.time_input("Entry Time", datetime.now().time())
    id_card = st.selectbox("ID Card Scanned?", ["Yes", "No"])
with col2:
    face_match = st.slider("Camera Face Match % (from camera module)", 0, 100, 85)
    medical = st.checkbox("Medical Certificate Submitted?")

# Camera - Streamlit inbuilt, no library needed
photo = st.camera_input("📷 Take Photo for Verification (Optional)")

# --- INFERENCE ENGINE ---
if st.button("Run Inference Engine - Mark Attendance", type="primary", use_container_width=True):
    if not name:
        st.warning("Enter Student Name first")
    else:
        status = ""
        rule = ""
        explanation = ""

        # Rule 6
        if medical:
            status = "Medical Leave"
            rule = "Rule 6"
            explanation = "IF Medical_Certificate = Yes THEN Attendance = Medical Leave"

        # Rule 7 - Proxy
        elif face_match < 50 and id_card == "Yes" and photo is not None:
            status = "Proxy Suspected"
            rule = "Rule 7"
            explanation = "IF Face < 50% AND ID=Yes THEN Proxy Suspected -> Alert Faculty"

        # Rule 1 - Present
        elif entry_time <= on_time and id_card == "Yes" and face_match >= face_needed:
            status = "Present"
            rule = "Rule 1"
            explanation = f"IF Time <= {on_time} AND ID=Yes AND Face>={face_needed}% THEN Present"

        # Rule 2 & 4 - Late logic
        elif entry_time <= late_limit and id_card == "Yes":
            count = st.session_state.late_count.get(name, 0) + 1
            st.session_state.late_count[name] = count

            if count >= lates_for_absent:
                status = "Absent"
                rule = "Rule 4"
                explanation = f"IF Late Count >= {lates_for_absent} THEN 1 Absent"
                st.session_state.late_count[name] = 0
            else:
                status = f"Late ({count}/{lates_for_absent})"
                rule = "Rule 2"
                explanation = f"IF Time <= {late_limit} THEN Late"

        # Rule 3 - Absent
        else:
            status = "Absent"
            rule = "Rule 3"
            explanation = f"IF Time > {late_limit} OR ID=No THEN Absent"

        # Save to Fact Base
        st.session_state.attendance.append({
            "Date": datetime.now().strftime("%d-%m-%Y"),
            "Name": name,
            "Time": entry_time.strftime("%H:%M"),
            "ID": id_card,
            "Face%": face_match,
            "Status": status,
            "Rule": rule,
            "Explanation": explanation
        })

        if "Present" in status:
            st.success(f"✅ {name} -> {status}")
        elif "Late" in status:
            st.warning(f"⚠️ {name} -> {status}")
        else:
            st.error(f"❌ {name} -> {status}")

        st.info(f"**{rule} Fired:** {explanation}")

# --- DISPLAY FACT BASE ---
if st.session_state.attendance:
    st.divider()
    st.subheader("📋 Fact Base - Attendance Sheet")
    st.dataframe(st.session_state.attendance, use_container_width=True)

    # Rule 5 - Defaulter
    st.subheader("🚨 Rule 5: Defaulter Check")
    names = {}
    for row in st.session_state.attendance:
        n = row["Name"]
        if n not in names:
            names[n] = {"total":0, "present":0}
        names[n]["total"] += 1
        if row["Status"] == "Present":
            names[n]["present"] += 1

    for student, data in names.items():
        perc = (data["present"] / data["total"]) * 100
        if perc < 75:
            st.error(f"{student}: {perc:.1f}% - DEFAULTER (Rule 5: IF <75% THEN Notify HOD)")
        else:
            st.write(f"{student}: {perc:.1f}% - OK")

    if st.button("Clear All Data"):
        st.session_state.attendance = []
        st.session_state.late_count = {}
        st.rerun()
