import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib

st.set_page_config(page_title="Hospitality CRM Enterprise", layout="wide")

conn = sqlite3.connect("hospitality.db", check_same_thread=False)
c = conn.cursor()

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ---------------- TABLES ---------------- #

c.execute("""CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT UNIQUE,
password TEXT,
role TEXT)""")

c.execute("""CREATE TABLE IF NOT EXISTS guests(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
mobile TEXT,
category TEXT,
visit_date TEXT,
staff_name TEXT)""")

c.execute("""CREATE TABLE IF NOT EXISTS feedback(
id INTEGER PRIMARY KEY AUTOINCREMENT,
guest_id INTEGER,
rating INTEGER,
service TEXT,
food TEXT,
behaviour TEXT,
comment TEXT,
date TEXT)""")

conn.commit()

# Create default admin
admin = pd.read_sql_query("SELECT * FROM users WHERE role='admin'", conn)
if admin.empty:
    c.execute("INSERT INTO users VALUES(NULL,?,?,?)",
              ("admin", hash_password("admin123"), "admin"))
    conn.commit()

# ---------------- FEEDBACK LINK ROUTE ---------------- #

query = st.query_params

if "fid" in query:

    guest_id = query["fid"]

    guest = pd.read_sql_query(
        "SELECT * FROM guests WHERE id=?",
        conn,
        params=(guest_id,)
    )

    if not guest.empty:

        st.title("⭐ Guest Feedback Form")

        st.write("Name:", guest["name"][0])
        st.write("Mobile:", guest["mobile"][0])

        rating = st.slider("Overall Rating", 1, 5)
        service = st.selectbox("Service", ["Excellent","Good","Average","Poor"])
        food = st.selectbox("Food", ["Excellent","Good","Average","Poor"])
        behaviour = st.selectbox("Behaviour", ["Excellent","Good","Average","Poor"])
        comment = st.text_area("Comment")

        if st.button("Submit Feedback"):
            c.execute("""INSERT INTO feedback
            VALUES(NULL,?,?,?,?,?,?,?)""",
                      (guest_id,rating,service,food,behaviour,comment,datetime.now()))
            conn.commit()
            st.success("Thank You ❤️")

    else:
        st.error("Invalid Link")

    st.stop()

# ---------------- LOGIN ---------------- #

if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = None

if st.session_state.user is None:

    st.title("🔐 Login")

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

    st.stop()

st.sidebar.write("Logged in as:", st.session_state.user)

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.session_state.role = None
    st.rerun()

role = st.session_state.role

# ================= STAFF PANEL ================= #

if role == "staff":

    st.title("👨‍💼 Staff Dashboard")

    st.subheader("➕ Add Entry")

    name = st.text_input("Guest Name")
    mobile = st.text_input("Mobile")
    category = st.selectbox("Source",
        ["Zomato","Swiggy","Easy Dinner","Party","Walk-In","VIP","Other"])
    visit_date = st.date_input("Visit Date")

    if st.button("Submit Entry"):
        c.execute("""INSERT INTO guests VALUES(NULL,?,?,?,?,?)""",
                  (name,mobile,category,visit_date,st.session_state.user))
        conn.commit()
        guest_id = c.lastrowid
        link = f"http://localhost:8501/?fid={guest_id}"
        st.success("Entry Saved")
        st.code(link)

    st.subheader("📅 Today's Entries")

    today = pd.read_sql_query("""
    SELECT * FROM guests
    WHERE staff_name=? AND visit_date=date('now')
    """, conn, params=(st.session_state.user,))
    st.dataframe(today)
    st.write("Total Today:", len(today))

    st.subheader("🔑 Change Password")
    col1,col2 = st.columns(2)
    with col1:
        new_pass = st.text_input("New Password", type="password")
    with col2:
        if st.button("Update Password"):
            c.execute("UPDATE users SET password=? WHERE username=?",
                      (hash_password(new_pass),st.session_state.user))
            conn.commit()
            st.success("Password Updated")

# ================= ADMIN PANEL ================= #

if role == "admin":

    st.title("👑 Admin Dashboard")

    menu = st.sidebar.radio("Admin Menu",
        ["Overview","Repeat Customers","Feedback Reports",
         "Manage Staff","Export Data","Change Password"])

    # OVERVIEW
    if menu == "Overview":
        data = pd.read_sql_query("SELECT * FROM guests", conn)
        st.dataframe(data)

        summary = pd.read_sql_query("""
        SELECT category,COUNT(*) as Total
        FROM guests GROUP BY category""", conn)
        st.bar_chart(summary.set_index("category"))

    # REPEAT
    if menu == "Repeat Customers":
        repeat = pd.read_sql_query("""
        SELECT name,mobile,COUNT(*) as Visits
        FROM guests
        GROUP BY mobile
        HAVING Visits>1""", conn)
        st.dataframe(repeat)

    # FEEDBACK
    if menu == "Feedback Reports":
        fb = pd.read_sql_query("""
        SELECT g.name,g.mobile,f.rating,f.comment,f.date
        FROM feedback f
        JOIN guests g ON f.guest_id=g.id""", conn)
        st.dataframe(fb)

        rating = pd.read_sql_query("""
        SELECT rating,COUNT(*) as Total
        FROM feedback GROUP BY rating""", conn)
        if not rating.empty:
            st.bar_chart(rating.set_index("rating"))

    # MANAGE STAFF
    if menu == "Manage Staff":

        st.subheader("Create Staff")
        username = st.text_input("Staff Name (Username)")
        password = st.text_input("Password", type="password")

        if st.button("Create"):
            c.execute("INSERT INTO users VALUES(NULL,?,?,?)",
                      (username,hash_password(password),"staff"))
            conn.commit()
            st.success("Staff Created")

        staff = pd.read_sql_query("SELECT username FROM users WHERE role='staff'", conn)
        st.dataframe(staff)

        remove = st.selectbox("Remove Staff",
                              staff["username"] if not staff.empty else [])
        if st.button("Delete"):
            c.execute("DELETE FROM users WHERE username=?", (remove,))
            conn.commit()
            st.success("Removed")

    # EXPORT
    if menu == "Export Data":
        g = pd.read_sql_query("SELECT * FROM guests", conn)
        f = pd.read_sql_query("SELECT * FROM feedback", conn)

        st.download_button("Download Guests CSV",
                           g.to_csv(index=False),
                           "guests.csv")

        st.download_button("Download Feedback CSV",
                           f.to_csv(index=False),
                           "feedback.csv")

    # PASSWORD
    if menu == "Change Password":
        new_pass = st.text_input("New Admin Password", type="password")
        if st.button("Update Admin Password"):
            c.execute("UPDATE users SET password=? WHERE username='admin'",
                      (hash_password(new_pass),))
            conn.commit()
            st.success("Password Updated")
