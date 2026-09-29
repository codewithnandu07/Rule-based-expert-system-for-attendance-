import streamlit as st
import pandas as pd
import face_recognition
import cv2
import numpy as np
import os
from datetime import datetime

st.set_page_config(page_title="Attendance Expert System", layout="wide")
st.title("🧠 Rule-Based Expert System with Face Recognition")

# --- LOAD KNOWN FACES (Knowledge Base Part 1) ---
@st.cache_data
def load_known_faces():
    known_encodings = {}
    path = "known_faces"
    if not os.path.exists(path):
        os.makedirs(path)
        return {}
    for file in os.listdir(path):
        if file.endswith((".jpg",".png",".jpeg")):
            name = os.path.splitext(file)[0]
            img = face_recognition.load_image_file(f"{path}/{file}")
            enc = face_recognition.face_encodings(img)
            if enc:
                known_encodings[name] = enc[0]
    return known_encodings

known_faces = load_known_faces()
st.sidebar.write(f"Loaded {len(known_faces)} known faces")

# --- RULE BASE (Sidebar) ---
st.sidebar.header("📜 Rule Base")
rule1_time = st.sidebar.time_input("On-Time Limit", datetime.strptime("09:10", "%H:%M").time())
rule2_late = st.sidebar.time_input("Late Limit", datetime.strptime("09:30", "%H:%M").time())
face_threshold = st.sidebar.slider("Face Match Threshold %", 0, 100, 60)
late_to_absent = st.sidebar.number_input("Lates = 1 Absent", 1, 10, 3)

if 'attendance' not in st.session_state:
    st.session_state.attendance = []
if 'late_count' not in st.session_state:
    st.session_state.late_count = {}

# --- INPUT SECTION ---
col1, col2 = st.columns(2)
with col1:
    name = st.selectbox("Select Student", list(known_faces.keys()) if known_faces else ["Rahul"])
    id_card = st.selectbox("ID Card Scanned?", ["Yes", "No"])
    medical = st.checkbox("Medical Certificate?")
    in_time = st.time_input("Entry Time", datetime.now().time())

with col2:
    st.subheader("📷 Camera Verification")
    cam_image = st.camera_input("Take a picture to verify face")

face_match = 0
if cam_image and name in known_faces:
    # Convert camera image to encoding
    file_bytes = np.asarray(bytearray(cam_image.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    face_encs = face_recognition.face_encodings(rgb_img)

    if face_encs:
        # Compare
        distance = face_recognition.face_distance([known_faces[name]], face_encs[0])[0]
        face_match = int((1 - distance) * 100)
        st.metric("Face Match", f"{face_match}%")
        if face_match >= face_threshold:
            st.success("Face Matched")
        else:
            st.error("Face NOT Matched - Possible Proxy")
    else:
        st.warning("No face detected")
        face_match = 0
elif cam_image:
    st.warning("No reference image found for this name. Add photo in known_faces folder.")

# --- INFERENCE ENGINE ---
if st.button("Mark Attendance", type="primary"):
    status = ""
    rule_fired = ""

    if medical:
        status = "Medical Leave"
        rule_fired = "Rule 6: IF Medical=Yes THEN Leave"
    elif face_match < 40 and id_card == "Yes" and cam_image:
        status = "Proxy Suspected"
        rule_fired = "Rule 7: Face < 40% + ID Yes -> Alert"
    elif in_time <= rule1_time and id_card == "Yes" and face_match >= face_threshold:
        status = "Present"
        rule_fired = f"Rule 1: On-Time + ID + Face>={face_threshold}"
    elif in_time <= rule2_late and id_card == "Yes":
        st.session_state.late_count[name] = st.session_state.late_count.get(name, 0) + 1
        if st.session_state.late_count[name] >= late_to_absent:
            status = f"Absent (Rule 4: {late_to_absent} Lates)"
            rule_fired = f"Rule 4: {late_to_absent} Lates = 1 Absent"
            st.session_state.late_count[name] = 0
        else:
            status = "Late"
            rule_fired = f"Rule 2: Late till {rule2_late}"
    else:
        status = "Absent"
        rule_fired = f"Rule 3: Time > {rule2_late} OR No ID"

    st.session_state.attendance.append({
        "Name": name, "Time": str(in_time),
        "Face %": face_match, "ID": id_card,
        "Status": status, "Rule Fired": rule_fired,
        "Date": datetime.now().strftime("%Y-%m-%d")
    })
    st.success(f"{name} marked as {status}")

# --- REPORT ---
if st.session_state.attendance:
    df = pd.DataFrame(st.session_state.attendance)
    st.divider()
    st.subheader("📋 Attendance Sheet (Fact Base)")
    st.dataframe(df, use_container_width=True)

    st.subheader("🚨 Defaulter System - Rule 5")
    total = df.groupby('Name').size()
    present = df[df['Status']=='Present'].groupby('Name').size()
    for student in total.index:
        p_count = present.get(student, 0)
        perc = (p_count / total[student]) * 100
        if perc < 75:
            st.error(f"{student}: {perc:.1f}% -> DEFAULTER - Notify HOD")
