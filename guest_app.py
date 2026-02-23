import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import urllib.parse

st.set_page_config(page_title="CARNIVALE - Hospitality CRM", layout="wide")

# ---------------- STYLE ---------------- #

st.markdown("""
<style>
.main-card {
    background-color: white;
    padding: 30px;
    border-radius: 15px;
    box-shadow: 0px 10px 25px rgba(0,0,0,0.1);
}
.big-title {
    font-size: 32px;
    font-weight: bold;
    color: #B03A2E;
}
.footer {
    text-align:center;
    font-size:12px;
    color:gray;
    margin-top:40px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- DATABASE ---------------- #

conn = sqlite3.connect("hospitality.db", check_same_thread=False)
c = conn.cursor()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# USERS TABLE
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT,
    can_add INTEGER DEFAULT 0,
    can_edit INTEGER DEFAULT 0,
    can_delete INTEGER DEFAULT 0,
    can_export INTEGER DEFAULT 0,
    can_view_reports INTEGER DEFAULT 0
)
""")

# GUESTS TABLE
c.execute("""
CREATE TABLE IF NOT EXISTS guests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    mobile TEXT,
    category TEXT,
    visit_date TEXT,
    staff_name TEXT
)
""")

# FEEDBACK TABLE
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
admin_check = pd.read_sql_query("SELECT * FROM users WHERE role='admin'", conn)
if admin_check.empty:
    c.execute("""
    INSERT INTO users 
    (username,password,role,can_add,can_edit,can_delete,can_export,can_view_reports)
    VALUES (?,?,?,?,?,?,?,?)
    """, ("admin", hash_password("admin123"), "admin",1,1,1,1,1))
    conn.commit()

# ---------------- PUBLIC FEEDBACK PAGE ---------------- #

query = st.query_params

if "feedback" in query:
    guest_id = query["feedback"]

    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown('<div class="big-title">CARNIVALE ❤️ We Value Your Feedback</div>', unsafe_allow_html=True)

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

    st.markdown('<div class="footer">Created by RJ_RAUNAK</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ---------------- LOGIN ---------------- #

if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = None

if st.session_state.user is None:

    st.title("CARNIVALE - Login")

    users = pd.read_sql_query(
        "SELECT username FROM users ORDER BY role DESC, username ASC",
        conn
    )

    selected_user = st.selectbox("Select Your ID", users["username"])
    password = st.text_input("Enter Password", type="password")

    if st.button("Login", use_container_width=True):
        user = pd.read_sql_query(
            "SELECT * FROM users WHERE username=? AND password=?",
            conn,
            params=(selected_user, hash_password(password))
        )

        if not user.empty:
            st.session_state.user = selected_user
            st.session_state.role = user["role"][0]
            st.rerun()
        else:
            st.error("Wrong Password")

    st.markdown('<div class="footer">Created by RJ_RAUNAK</div>', unsafe_allow_html=True)
    st.stop()

role = st.session_state.role

# ---------------- LOGOUT BUTTON ---------------- #

st.sidebar.write(f"Logged in as: {st.session_state.user}")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.session_state.role = None
    st.rerun()

# ---------------- STAFF PANEL ---------------- #

if role == "staff":

    st.title("CARNIVALE - Staff Dashboard")

    user_data = pd.read_sql_query(
        "SELECT * FROM users WHERE username=?",
        conn,
        params=(st.session_state.user,)
    ).iloc[0]

    if user_data["can_add"] == 1:
        st.subheader("Add Guest Entry")

        name = st.text_input("Guest Name")
        mobile = st.text_input("Mobile")

        category = st.selectbox(
            "Category",
            ["Swiggy", "Zomato", "Party", "Easy Dinner", "VIP", "Walk-in", "Other"]
        )

        visit_date = st.date_input("Visit Date")

        if st.button("Submit Entry"):

            c.execute("""
            INSERT INTO guests (name,mobile,category,visit_date,staff_name)
            VALUES (?,?,?,?,?)
            """,(name,mobile,category,visit_date,st.session_state.user))
            conn.commit()

            guest_id = c.lastrowid

            base_url = st.request.host_url.rstrip("/")
            feedback_link = f"{base_url}/?feedback={guest_id}"

            message = f"""Thank you for visiting CARNIVALE 🙏

Please share your valuable feedback:
{feedback_link}
"""

            encoded_message = urllib.parse.quote(message)
            whatsapp_link = f"https://wa.me/?text={encoded_message}"

            st.success("Entry Added Successfully ✅")
            st.link_button("📲 Send on WhatsApp", whatsapp_link)
            st.code(feedback_link)

    my_data = pd.read_sql_query(
        "SELECT * FROM guests WHERE staff_name=?",
        conn,
        params=(st.session_state.user,)
    )

    st.subheader("My Entries")
    st.dataframe(my_data)

    st.markdown('<div class="footer">Created by RJ_RAUNAK</div>', unsafe_allow_html=True)

# ---------------- ADMIN PANEL ---------------- #

if role == "admin":

    st.title("CARNIVALE - Admin Dashboard")

    menu = st.sidebar.radio("Menu",
        ["Overview","Create Staff","Reports","Delete Guest","Export All","Change Password"])

    if menu == "Overview":
        data = pd.read_sql_query("SELECT * FROM guests", conn)
        st.dataframe(data)

    if menu == "Create Staff":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        can_add = st.checkbox("Can Add")
        can_edit = st.checkbox("Can Edit")
        can_delete = st.checkbox("Can Delete")
        can_export = st.checkbox("Can Export")
        can_view_reports = st.checkbox("Can View Reports")

        if st.button("Create Staff"):
            c.execute("""
            INSERT INTO users
            (username,password,role,can_add,can_edit,can_delete,can_export,can_view_reports)
            VALUES (?,?,?,?,?,?,?,?)
            """,(username,hash_password(password),"staff",
                 int(can_add),int(can_edit),int(can_delete),
                 int(can_export),int(can_view_reports)))
            conn.commit()
            st.success("Staff Created")

    if menu == "Reports":

        st.subheader("Repeat Customers")
        repeat = pd.read_sql_query("""
        SELECT name,mobile,COUNT(*) as visits
        FROM guests
        GROUP BY mobile
        HAVING visits>1
        """, conn)
        st.dataframe(repeat)

        st.subheader("Feedback Report")
        feedback_data = pd.read_sql_query("""
        SELECT g.name,g.mobile,
        f.food,f.service,f.behaviour,
        f.ambience,f.cleanliness,
        f.comment,f.date
        FROM feedback f
        JOIN guests g ON f.guest_id=g.id
        """, conn)
        st.dataframe(feedback_data)

    if menu == "Delete Guest":
        del_id = st.number_input("Guest ID", step=1)
        if st.button("Delete"):
            c.execute("DELETE FROM guests WHERE id=?", (del_id,))
            conn.commit()
            st.success("Deleted")

    if menu == "Export All":
        data = pd.read_sql_query("SELECT * FROM guests", conn)
        st.download_button("Download CSV",
                           data.to_csv(index=False),
                           "all_data.csv")

    if menu == "Change Password":
        new_pass = st.text_input("New Password", type="password")
        if st.button("Update Admin Password"):
            c.execute("UPDATE users SET password=? WHERE username='admin'",
                      (hash_password(new_pass),))
            conn.commit()
            st.success("Password Updated")

    st.markdown('<div class="footer">Created by RJ_RAUNAK</div>', unsafe_allow_html=True)
