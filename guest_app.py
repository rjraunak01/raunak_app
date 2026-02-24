import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import pagesizes
import os

st.set_page_config(page_title="CARNIVALE PRO", layout="wide")

# ================= DATABASE =================

conn = sqlite3.connect("carnivale.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS branches(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS staff(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
branch TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS guests(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
mobile TEXT,
branch TEXT,
staff TEXT,
date TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS feedback(
id INTEGER PRIMARY KEY AUTOINCREMENT,
guest_id INTEGER,
food INTEGER,
service INTEGER,
behaviour INTEGER,
ambience INTEGER,
cleanliness INTEGER,
comment TEXT,
date TEXT
)""")

conn.commit()

# ================= UI HEADER =================

st.markdown("""
<h1 style='text-align:center;color:#D4AF37;'>🎭 CARNIVALE MANAGEMENT SYSTEM</h1>
""", unsafe_allow_html=True)

menu = st.sidebar.selectbox("Select Module",
["Add Branch","Add Staff","Guest Entry","Feedback Form","Dashboard","Salary System","Generate PDF"])

# ================= ADD BRANCH =================

if menu=="Add Branch":
    st.subheader("🏢 Add Branch")
    name = st.text_input("Branch Name")
    if st.button("Add Branch"):
        c.execute("INSERT INTO branches(name) VALUES(?)",(name,))
        conn.commit()
        st.success("Branch Added")

# ================= ADD STAFF =================

if menu=="Add Staff":
    st.subheader("👨‍💼 Add Staff")
    branches = pd.read_sql("SELECT name FROM branches",conn)
    branch = st.selectbox("Select Branch",branches)
    name = st.text_input("Staff Name")
    if st.button("Add Staff"):
        c.execute("INSERT INTO staff(name,branch) VALUES(?,?)",(name,branch))
        conn.commit()
        st.success("Staff Added")

# ================= GUEST ENTRY =================

if menu=="Guest Entry":
    st.subheader("📝 Guest Entry")
    branches = pd.read_sql("SELECT name FROM branches",conn)
    staff = pd.read_sql("SELECT name FROM staff",conn)

    name = st.text_input("Guest Name")
    mobile = st.text_input("Mobile")
    branch = st.selectbox("Branch",branches)
    staff_name = st.selectbox("Handled By Staff",staff)

    if st.button("Submit Entry"):
        c.execute("INSERT INTO guests(name,mobile,branch,staff,date) VALUES(?,?,?,?,?)",
                  (name,mobile,branch,staff_name,str(datetime.now())))
        conn.commit()
        st.success("Entry Saved")

# ================= FEEDBACK FORM =================

if menu=="Feedback Form":
    st.subheader("⭐ Premium Feedback")

    guests = pd.read_sql("SELECT id,name,mobile FROM guests ORDER BY id DESC",conn)
    guest_select = st.selectbox("Select Guest",guests["name"]+" - "+guests["mobile"])

    food = st.slider("🍽 Food",1,5)
    service = st.slider("🤵 Service",1,5)
    behaviour = st.slider("🙂 Behaviour",1,5)
    ambience = st.slider("🏨 Ambience",1,5)
    cleanliness = st.slider("🧹 Cleanliness",1,5)
    comment = st.text_area("Comment")

    if st.button("Submit Feedback"):
        guest_id = guests.iloc[
            guests["name"]+" - "+guests["mobile"]==guest_select].id.values[0]
        c.execute("""INSERT INTO feedback
        (guest_id,food,service,behaviour,ambience,cleanliness,comment,date)
        VALUES(?,?,?,?,?,?,?,?)""",
        (guest_id,food,service,behaviour,ambience,cleanliness,comment,str(datetime.now())))
        conn.commit()
        st.success("Feedback Submitted 🎉")

# ================= DASHBOARD =================

if menu=="Dashboard":
    st.subheader("📊 Analytics Dashboard")

    total_guests = pd.read_sql("SELECT COUNT(*) as c FROM guests",conn)["c"][0]
    total_feedback = pd.read_sql("SELECT COUNT(*) as c FROM feedback",conn)["c"][0]

    col1,col2 = st.columns(2)
    col1.metric("Total Guests",total_guests)
    col2.metric("Total Feedback",total_feedback)

    repeat = pd.read_sql("""
    SELECT mobile, COUNT(id) as visits
    FROM guests GROUP BY mobile HAVING visits>1
    """,conn)

    st.subheader("🔁 Repeat Guests")
    st.dataframe(repeat)

# ================= SALARY SYSTEM =================

if menu=="Salary System":
    st.subheader("💰 Staff Performance Salary")

    df = pd.read_sql("""
    SELECT g.staff, AVG(
    (f.food+f.service+f.behaviour+f.ambience+f.cleanliness)/5.0
    ) as avg_rating, COUNT(f.id) as total_feedback
    FROM feedback f
    JOIN guests g ON f.guest_id=g.id
    GROUP BY g.staff
    """,conn)

    if not df.empty:
        df["performance_bonus"] = df["avg_rating"]*1000
        st.dataframe(df)

# ================= PDF REPORT =================

if menu=="Generate PDF":
    st.subheader("📄 Generate Report PDF")

    data = pd.read_sql("""
    SELECT g.name,g.mobile,g.branch,g.staff,f.comment,f.date
    FROM feedback f
    JOIN guests g ON f.guest_id=g.id
    """,conn)

    if st.button("Generate PDF"):
        file="carnivale_report.pdf"
        doc = SimpleDocTemplate(file,pagesize=pagesizes.A4)
        elements=[]
        styles=getSampleStyleSheet()
        elements.append(Paragraph("CARNIVALE REPORT",styles["Title"]))
        elements.append(Spacer(1,12))
        table_data=[list(data.columns)]+data.values.tolist()
        t=Table(table_data)
        t.setStyle([('BACKGROUND',(0,0),(-1,0),colors.gold),
                    ('GRID',(0,0),(-1,-1),1,colors.black)])
        elements.append(t)
        doc.build(elements)
        with open(file,"rb") as f:
            st.download_button("Download PDF",f,file)
