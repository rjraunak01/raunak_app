import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib

st.set_page_config(page_title="Hospitality CRM PRO", layout="wide")

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
    font-size: 30px;
    font-weight: bold;
    color: #1F618D;
}
.section-title {
    font-size: 18px;
    font-weight: 600;
    margin-top: 15px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- DATABASE ---------------- #

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
    role TEXT,
    can_add INTEGER DEFAULT 0,
    can_edit INTEGER DEFAULT 0,
    can_delete INTEGER DEFAULT 0,
    can_export INTEGER DEFAULT 0,
    can_view_reports INTEGER DEFAULT 0
)
""")

# GUESTS
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
    st.markdown('<div class="big-title">We Value Your Feedback ❤️</div>', unsafe_allow_html=True)

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
        st.success("Thank You For Visiting 🙏")
        st.balloons()

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ---------------- LOGIN ---------------- #

if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = None

if st.session_state.user is None:

    st.title("Login")

    users = pd.read_sql_query("SELECT username FROM users", conn)

    selected_user = st.selectbox("Select User", users["username"])
    password = st.text_input("Password", type="password")

    if st.button("Login"):
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

    st.stop()

role = st.session_state.role

# ---------------- STAFF PANEL ---------------- #

if role == "staff":

    st.title("Staff Dashboard")

    user_data = pd.read_sql_query(
        "SELECT * FROM users WHERE username=?",
        conn,
        params=(st.session_state.user,)
    ).iloc[0]

    if user_data["can_add"] == 1:
        st.subheader("Add Entry")
        name = st.text_input("Guest Name")
        mobile = st.text_input("Mobile")
        category = st.text_input("Source")
        visit_date = st.date_input("Visit Date")

        if st.button("Submit Entry"):
            c.execute("""
            INSERT INTO guests (name,mobile,category,visit_date,staff_name)
            VALUES (?,?,?,?,?)
            """,(name,mobile,category,visit_date,st.session_state.user))
            conn.commit()
            guest_id = c.lastrowid
            st.success("Entry Added")

            feedback_link = f"http://localhost:8501/?feedback={guest_id}"
            st.write("Send this feedback link to guest:")
            st.code(feedback_link)

    my_data = pd.read_sql_query("""
    SELECT * FROM guests WHERE staff_name=?
    """, conn, params=(st.session_state.user,))

    st.subheader("My Entries")
    st.dataframe(my_data)

    st.write("Today Entries:",
             len(my_data[my_data["visit_date"] == str(datetime.today().date())]))

    if user_data["can_edit"] == 1:
        edit_id = st.number_input("Edit ID", step=1)
        new_name = st.text_input("New Name")
        if st.button("Update"):
            c.execute("""
            UPDATE guests SET name=?
            WHERE id=? AND staff_name=?
            """,(new_name,edit_id,st.session_state.user))
            conn.commit()
            st.success("Updated")

    if user_data["can_export"] == 1:
        st.download_button("Export My Data",
                           my_data.to_csv(index=False),
                           "my_data.csv")

    st.subheader("Change Password")
    new_pass = st.text_input("New Password", type="password")
    if st.button("Change Password"):
        c.execute("UPDATE users SET password=? WHERE username=?",
                  (hash_password(new_pass),st.session_state.user))
        conn.commit()
        st.success("Password Updated")

# ---------------- ADMIN PANEL ---------------- #

if role == "admin":

    st.title("Admin Dashboard")

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
