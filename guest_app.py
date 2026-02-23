import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib

st.set_page_config(page_title="Hospitality CRM Pro", layout="wide")

# ---------------- DATABASE ---------------- #

conn = sqlite3.connect("hospitality.db", check_same_thread=False)
c = conn.cursor()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Users Table
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

# Guests Table
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

# Feedback Table
c.execute("""
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id INTEGER,
    rating INTEGER,
    service TEXT,
    food TEXT,
    behaviour TEXT,
    comment TEXT,
    date TEXT
)
""")

conn.commit()

# Default Admin Create
admin_check = pd.read_sql_query("SELECT * FROM users WHERE role='admin'", conn)
if admin_check.empty:
    c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
              ("admin", hash_password("admin123"), "admin"))
    conn.commit()

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
            st.success("Login Successful")
            st.rerun()
        else:
            st.error("Invalid Credentials")

    st.stop()

# ---------------- LOGOUT ---------------- #

st.sidebar.write("Logged in as:", st.session_state.user)
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.session_state.role = None
    st.rerun()

role = st.session_state.role

# ---------------- STAFF PANEL ---------------- #

if role == "staff":

    st.title("👨‍💼 Staff Dashboard")

    st.subheader("➕ Add Entry")

    name = st.text_input("Guest Name")
    mobile = st.text_input("Mobile")
    category = st.selectbox("Source", ["Zomato","Swiggy","Easy Dinner","Party","Walk-In","VIP","Other"])
    visit_date = st.date_input("Visit Date")

    if st.button("Submit"):
        c.execute("""
        INSERT INTO guests (name, mobile, category, visit_date, staff_name)
        VALUES (?,?,?,?,?)
        """, (name, mobile, category, visit_date, st.session_state.user))
        conn.commit()
        st.success("Entry Added")

    st.subheader("📅 Today's Entries")

    today = pd.read_sql_query("""
    SELECT * FROM guests
    WHERE staff_name=? AND visit_date=date('now')
    """, conn, params=(st.session_state.user,))
    st.dataframe(today)
    st.write("Total Today:", len(today))

    st.subheader("✏ Edit My Entries")

    my_data = pd.read_sql_query("""
    SELECT * FROM guests WHERE staff_name=?
    """, conn, params=(st.session_state.user,))

    st.dataframe(my_data)

    edit_id = st.number_input("Enter ID to Edit", step=1)

    if st.button("Load Entry"):
        entry = pd.read_sql_query("SELECT * FROM guests WHERE id=?", conn, params=(edit_id,))
        if not entry.empty:
            st.session_state.editing = edit_id

    if "editing" in st.session_state:
        new_name = st.text_input("New Name")
        if st.button("Update Entry"):
            c.execute("UPDATE guests SET name=? WHERE id=?",
                      (new_name, st.session_state.editing))
            conn.commit()
            st.success("Updated")
            del st.session_state.editing

    st.subheader("🔑 Change Password")
    new_pass = st.text_input("New Password", type="password")
    if st.button("Change Password"):
        c.execute("UPDATE users SET password=? WHERE username=?",
                  (hash_password(new_pass), st.session_state.user))
        conn.commit()
        st.success("Password Updated")

# ---------------- ADMIN PANEL ---------------- #

if role == "admin":

    st.title("👑 Admin Dashboard")

    page = st.sidebar.radio("Admin Menu", ["Overview","Manage Staff","Edit Data","Export Data","Change Password"])

    if page == "Overview":
        data = pd.read_sql_query("SELECT * FROM guests", conn)
        st.dataframe(data)
        summary = pd.read_sql_query("""
        SELECT category, COUNT(*) as Total FROM guests GROUP BY category
        """, conn)
        st.bar_chart(summary.set_index("category"))

    if page == "Manage Staff":
        st.subheader("Add Staff")
        new_staff = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")
        if st.button("Create Staff"):
            try:
                c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                          (new_staff, hash_password(new_pass), "staff"))
                conn.commit()
                st.success("Staff Created")
            except:
                st.error("User Exists")

        staff_list = pd.read_sql_query("SELECT username FROM users WHERE role='staff'", conn)
        st.dataframe(staff_list)

        remove = st.selectbox("Remove Staff", staff_list["username"] if not staff_list.empty else [])
        if st.button("Delete Staff"):
            c.execute("DELETE FROM users WHERE username=?", (remove,))
            conn.commit()
            st.success("Staff Removed")

    if page == "Edit Data":
        data = pd.read_sql_query("SELECT * FROM guests", conn)
        st.dataframe(data)

        edit_id = st.number_input("ID to Edit", step=1)
        new_name = st.text_input("New Name")
        if st.button("Update Data"):
            c.execute("UPDATE guests SET name=? WHERE id=?", (new_name, edit_id))
            conn.commit()
            st.success("Updated")

    if page == "Export Data":
        data = pd.read_sql_query("SELECT * FROM guests", conn)
        st.download_button("Download CSV", data.to_csv(index=False), "data.csv")

    if page == "Change Password":
        new_pass = st.text_input("New Password", type="password")
        if st.button("Change Admin Password"):
            c.execute("UPDATE users SET password=? WHERE username='admin'",
                      (hash_password(new_pass),))
            conn.commit()
            st.success("Password Updated")
