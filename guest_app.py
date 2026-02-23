import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Hospitality CRM Pro", layout="wide")

# ---------------- DATABASE ---------------- #

conn = sqlite3.connect("hospitality.db", check_same_thread=False)
c = conn.cursor()

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

# Staff Table
c.execute("""
CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_name TEXT UNIQUE
)
""")

conn.commit()

# ---------------- CHECK FEEDBACK LINK ---------------- #

query_params = st.query_params

if "feedback_id" in query_params:

    guest_id = query_params["feedback_id"]

    guest = pd.read_sql_query(
        "SELECT * FROM guests WHERE id=?",
        conn,
        params=(guest_id,)
    )

    if not guest.empty:

        st.title("⭐ Guest Feedback Form")

        st.write("Guest Name:", guest["name"][0])
        st.write("Mobile:", guest["mobile"][0])

        rating = st.slider("Overall Rating", 1, 5)
        service = st.selectbox("Service", ["Excellent", "Good", "Average", "Poor"])
        food = st.selectbox("Food", ["Excellent", "Good", "Average", "Poor"])
        behaviour = st.selectbox("Behaviour", ["Excellent", "Good", "Average", "Poor"])
        comment = st.text_area("Additional Comments")

        if st.button("Submit Feedback"):
            c.execute("""
            INSERT INTO feedback
            (guest_id, rating, service, food, behaviour, comment, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (guest_id, rating, service, food, behaviour, comment, datetime.now().date()))
            conn.commit()
            st.success("Thank You ❤️")

    else:
        st.error("Invalid Feedback Link")

    st.stop()

# ---------------- SIDEBAR ---------------- #

st.sidebar.title("📌 Navigation")
page = st.sidebar.radio("Go To", ["Guest Entry", "Admin Panel"])

# ---------------- GUEST ENTRY ---------------- #

if page == "Guest Entry":

    st.title("📝 Visitor Entry Form")

    staff_list = pd.read_sql_query("SELECT staff_name FROM staff", conn)
    staff_names = staff_list["staff_name"].tolist()

    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Guest Name")
        mobile = st.text_input("Mobile Number")

    with col2:
        category = st.selectbox("Booking Source", [
            "Zomato",
            "Swiggy",
            "Easy Dinner",
            "Party",
            "Walk-In",
            "VIP",
            "Other"
        ])
        staff = st.selectbox("Staff Name", staff_names if staff_names else ["No Staff Added"])

    if st.button("Submit Entry"):
        if name and mobile and staff != "No Staff Added":
            c.execute("""
            INSERT INTO guests (name, mobile, category, visit_date, staff_name)
            VALUES (?, ?, ?, ?, ?)
            """, (name, mobile, category, datetime.now().date(), staff))
            conn.commit()

            guest_id = c.lastrowid
            feedback_link = f"http://localhost:8501/?feedback_id={guest_id}"

            st.success("Entry Saved Successfully ✅")
            st.write("📩 Send this feedback link to guest:")
            st.code(feedback_link)

        else:
            st.error("Please fill all required fields")

# ---------------- ADMIN PANEL ---------------- #

elif page == "Admin Panel":

    st.title("🔐 Admin Login")
    password = st.text_input("Enter Password", type="password")

    if password == "admin123":

        st.success("Login Successful ✅")

        # -------- STAFF MANAGEMENT -------- #

        st.subheader("👨‍💼 Staff Management")

        new_staff = st.text_input("Add New Staff")
        if st.button("Add Staff"):
            if new_staff:
                try:
                    c.execute("INSERT INTO staff (staff_name) VALUES (?)", (new_staff,))
                    conn.commit()
                    st.success("Staff Added")
                except:
                    st.error("Staff Already Exists")

        staff_data = pd.read_sql_query("SELECT * FROM staff", conn)
        st.dataframe(staff_data)

        remove_staff = st.selectbox("Remove Staff", staff_data["staff_name"] if not staff_data.empty else [])
        if st.button("Remove Staff"):
            c.execute("DELETE FROM staff WHERE staff_name=?", (remove_staff,))
            conn.commit()
            st.success("Staff Removed")

        # -------- REPORTS -------- #

        st.subheader("📅 Today's Entries")
        today = pd.read_sql_query("""
        SELECT * FROM guests WHERE visit_date=date('now')
        """, conn)
        st.dataframe(today)

        st.subheader("📊 Booking Source Summary")
        summary = pd.read_sql_query("""
        SELECT category, COUNT(*) as Total
        FROM guests
        GROUP BY category
        """, conn)
        st.dataframe(summary)
        if not summary.empty:
            st.bar_chart(summary.set_index("category"))

        st.subheader("⭐ Feedback Overview")

        feedback_data = pd.read_sql_query("""
        SELECT g.name, g.mobile, f.rating, f.service, f.food, f.behaviour, f.comment, f.date
        FROM feedback f
        JOIN guests g ON f.guest_id = g.id
        """, conn)

        st.dataframe(feedback_data)

    elif password != "":
        st.error("Wrong Password ❌")
