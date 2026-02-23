import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import urllib.parse
import qrcode
from io import BytesIO
import plotly.express as px

# ================== CONFIG ==================

st.set_page_config(
    page_title="CARNIVALE - Premium CRM",
    layout="wide"
)

APP_URL = "https://your-real-app-name.streamlit.app"

# Dark Luxury UI
st.markdown("""
<style>
body {background-color: #0f0f0f; color:white;}
.stButton>button {background:#C19A6B;color:white;border-radius:10px;}
</style>
""", unsafe_allow_html=True)

# ================== DATABASE ==================

conn = sqlite3.connect("hospitality.db", check_same_thread=False)
c = conn.cursor()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# USERS
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

# GUESTS
c.execute("""
CREATE TABLE IF NOT EXISTS guests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    mobile TEXT,
    category TEXT,
    pax INTEGER,
    visit_date TEXT,
    staff_name TEXT
)
""")

# FEEDBACK
c.execute("""
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id INTEGER,
    food INTEGER,
    service INTEGER,
    behaviour INTEGER,
    ambience INTEGER,
    cleanliness INTEGER,
    comment TEXT,
    date TEXT
)
""")

conn.commit()

# Default Admin
admin = pd.read_sql("SELECT * FROM users WHERE username='admin'", conn)
if admin.empty:
    c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
              ("admin", hash_password("admin123"), "admin"))
    conn.commit()

# ================== SESSION TIMEOUT ==================

if "last_active" not in st.session_state:
    st.session_state.last_active = datetime.now()

if datetime.now() - st.session_state.last_active > timedelta(minutes=30):
    st.session_state.user = None
    st.session_state.role = None

st.session_state.last_active = datetime.now()

# ================== FEEDBACK PAGE ==================

query = st.query_params

if "feedback" in query:

    guest_id = query["feedback"]

    st.title("🌟 CARNIVALE Premium Feedback")

    food = st.slider("🍽 Food",1,5)
    service = st.slider("🛎 Service",1,5)
    behaviour = st.slider("😊 Behaviour",1,5)
    ambience = st.slider("✨ Ambience",1,5)
    cleanliness = st.slider("🧼 Cleanliness",1,5)
    comment = st.text_area("Your Comments")

    if st.button("Submit Feedback"):
        c.execute("""
        INSERT INTO feedback
        (guest_id,food,service,behaviour,ambience,cleanliness,comment,date)
        VALUES (?,?,?,?,?,?,?,?)
        """,(guest_id,food,service,behaviour,ambience,cleanliness,
             comment,datetime.now()))
        conn.commit()

        st.success("Thank You For Visiting CARNIVALE ❤️")
        st.balloons()

    st.stop()

# ================== LOGIN ==================

if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = None

if st.session_state.user is None:

    st.title("CARNIVALE Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = pd.read_sql(
            "SELECT * FROM users WHERE username=? AND password=?",
            conn,
            params=(username, hash_password(password))
        )
        if not user.empty:
            st.session_state.user = username
            st.session_state.role = user["role"][0]
            st.rerun()
        else:
            st.error("Invalid Credentials")

    st.stop()

# ================== SIDEBAR ==================

st.sidebar.write(f"👤 {st.session_state.user}")
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.session_state.role = None
    st.rerun()

# ================== ADMIN ==================

if st.session_state.role == "admin":

    st.sidebar.markdown("### Admin Control")

    if st.sidebar.button("Export All Data"):
        df = pd.read_sql("SELECT * FROM guests", conn)
        df.to_csv("export.csv", index=False)
        st.sidebar.success("Exported")

# ================== GUEST ENTRY ==================

st.title("🏨 CARNIVALE Guest Entry")

name = st.text_input("Guest Name")
mobile = st.text_input("Mobile")
category = st.selectbox("Category",
                        ["Walk-in","VIP","Swiggy","Zomato","Party"])
pax = st.number_input("PAX", min_value=1)
visit_date = st.date_input("Visit Date")

if st.button("Add Guest"):

    c.execute("""
    INSERT INTO guests (name,mobile,category,pax,visit_date,staff_name)
    VALUES (?,?,?,?,?,?)
    """,(name,mobile,category,pax,visit_date,st.session_state.user))
    conn.commit()

    guest_id = c.lastrowid

    feedback_link = f"{APP_URL}/?feedback={guest_id}"

    message = f"Thank you for visiting CARNIVALE 🙏\nPlease share feedback:\n{feedback_link}"
    encoded = urllib.parse.quote(message)
    whatsapp_link = f"https://wa.me/?text={encoded}"

    st.success("Guest Added ✅")

    st.link_button("📲 Send WhatsApp", whatsapp_link)
    st.code(feedback_link)

    # QR
    qr = qrcode.make(feedback_link)
    buf = BytesIO()
    qr.save(buf)
    st.image(buf)

# ================== DASHBOARD ==================

st.subheader("📊 Dashboard")

feedback_data = pd.read_sql("SELECT * FROM feedback", conn)

if not feedback_data.empty:

    feedback_data["avg"] = feedback_data[
        ["food","service","behaviour","ambience","cleanliness"]
    ].mean(axis=1)

    overall = round(feedback_data["avg"].mean(),2)

    st.metric("⭐ Overall Rating", overall)

    fig = px.bar(
        feedback_data,
        x="guest_id",
        y="avg",
        title="Guest Rating Graph"
    )
    st.plotly_chart(fig)

else:
    st.info("No Feedback Yet")
