import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import urllib.parse

# ================= CONFIG ================= #

st.set_page_config(page_title="CARNIVALE - Hospitality CRM", layout="wide")

APP_URL = "https://your-real-app-name.streamlit.app"  # 🔴 PUT REAL URL

# ================= DATABASE ================= #

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

# DEFAULT ADMIN
admin_check = pd.read_sql_query("SELECT * FROM users WHERE username='admin'", conn)
if admin_check.empty:
    c.execute("""
    INSERT INTO users (username,password,role)
    VALUES (?,?,?)
    """, ("admin", hash_password("admin123"), "admin"))
    conn.commit()

# ================= FEEDBACK PAGE ================= #

query = st.query_params

if "feedback" in query:
    guest_id = query["feedback"]

    st.title("CARNIVALE ❤️ We Value Your Feedback")

    food = st.slider("🍽 Food Quality",1,5)
    service = st.slider("🛎 Service",1,5)
    behaviour = st.slider("😊 Staff Behaviour",1,5)
    ambience = st.slider("✨ Ambience",1,5)
    cleanliness = st.slider("🧼 Cleanliness",1,5)
    comment = st.text_area("Additional Comments")

    if st.button("Submit Feedback"):
        c.execute("""
        INSERT INTO feedback
        (guest_id,food,service,behaviour,ambience,cleanliness,comment,date)
        VALUES (?,?,?,?,?,?,?,?)
        """,(guest_id,food,service,behaviour,ambience,cleanliness,
             comment,datetime.now()))
        conn.commit()
        st.success("Thank You For Visiting CARNIVALE 🙏")
        st.balloons()

    st.markdown("<center><small>Created by RJ_RAUNAK</small></center>", unsafe_allow_html=True)
    st.stop()

# ================= SESSION ================= #

if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = None

# ================= LOGIN ================= #

if st.session_state.user is None:

    st.title("CARNIVALE - Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = pd.read_sql_query(
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

    st.markdown("<center><small>Created by RJ_RAUNAK</small></center>", unsafe_allow_html=True)
    st.stop()

# ================= LOGOUT ================= #

st.sidebar.write(f"Logged in as: {st.session_state.user}")
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.session_state.role = None
    st.rerun()

# ================= ADMIN PANEL ================= #

if st.session_state.role == "admin":

    st.sidebar.markdown("## 🔐 Admin Panel")

    # ADD USER
    with st.sidebar.expander("➕ Add User"):
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        new_role = st.selectbox("Role", ["staff", "admin"])

        if st.button("Create User"):
            try:
                c.execute("""
                INSERT INTO users (username,password,role)
                VALUES (?,?,?)
                """,(new_user, hash_password(new_pass), new_role))
                conn.commit()
                st.success("User Created")
            except:
                st.error("Username exists")

    # RESET PASSWORD
    with st.sidebar.expander("🔄 Reset Password"):
        users_list = pd.read_sql_query("SELECT username FROM users", conn)
        selected_user = st.selectbox("Select User", users_list["username"])
        new_password = st.text_input("New Password", type="password")

        if st.button("Update Password"):
            c.execute("""
            UPDATE users SET password=? WHERE username=?
            """,(hash_password(new_password), selected_user))
            conn.commit()
            st.success("Password Updated")

    # DELETE USER
    with st.sidebar.expander("❌ Delete User"):
        users_list = pd.read_sql_query("SELECT username FROM users WHERE username!='admin'", conn)
        del_user = st.selectbox("Select User to Delete", users_list["username"])

        if st.button("Delete User"):
            c.execute("DELETE FROM users WHERE username=?", (del_user,))
            conn.commit()
            st.success("User Deleted")

    # VIEW USERS
    with st.sidebar.expander("👥 View Users"):
        users_data = pd.read_sql_query("SELECT id,username,role FROM users", conn)
        st.dataframe(users_data)

# ================= GUEST ENTRY ================= #

if st.session_state.role in ["admin","staff"]:

    st.title("CARNIVALE - Guest Entry")

    name = st.text_input("Guest Name")
    mobile = st.text_input("Mobile Number")
    category = st.selectbox(
        "Category",
        ["Swiggy", "Zomato", "Party", "Easy Dinner", "VIP", "Walk-in", "Other"]
    )
    pax = st.number_input("Number of Guests (PAX)", min_value=1, step=1)
    visit_date = st.date_input("Visit Date")

    if st.button("Submit Entry"):

        if name == "" or mobile == "":
            st.warning("Fill required fields")
        else:
            c.execute("""
            INSERT INTO guests (name,mobile,category,pax,visit_date,staff_name)
            VALUES (?,?,?,?,?,?)
            """,(name,mobile,category,pax,visit_date,st.session_state.user))
            conn.commit()

            guest_id = c.lastrowid
            feedback_link = f"{APP_URL}/?feedback={guest_id}"

            message = f"""Thank you for visiting CARNIVALE 🙏

Please share your valuable feedback:
{feedback_link}
"""
            encoded = urllib.parse.quote(message)
            whatsapp_link = f"https://wa.me/?text={encoded}"

            st.success("Entry Added Successfully ✅")
            st.link_button("📲 Send on WhatsApp", whatsapp_link)
            st.code(feedback_link)

    st.subheader("All Guest Entries")
    data = pd.read_sql_query("SELECT * FROM guests", conn)
    st.dataframe(data)

    # ================= ANALYTICS ================= #

    st.subheader("📊 Feedback Analytics")

    feedback_data = pd.read_sql_query("SELECT * FROM feedback", conn)

    if not feedback_data.empty:
        avg_food = round(feedback_data["food"].mean(),2)
        avg_service = round(feedback_data["service"].mean(),2)
        avg_behaviour = round(feedback_data["behaviour"].mean(),2)
        avg_ambience = round(feedback_data["ambience"].mean(),2)
        avg_clean = round(feedback_data["cleanliness"].mean(),2)

        st.write("Average Ratings:")
        st.write(f"Food: {avg_food}")
        st.write(f"Service: {avg_service}")
        st.write(f"Behaviour: {avg_behaviour}")
        st.write(f"Ambience: {avg_ambience}")
        st.write(f"Cleanliness: {avg_clean}")
    else:
        st.info("No feedback yet")

    st.markdown("<center><small>Created by RJ_RAUNAK</small></center>", unsafe_allow_html=True)
