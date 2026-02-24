import streamlit as st
import sqlite3
import pandas as pd
import uuid
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="CARNIVALE PRO", layout="wide")

# ================= DATABASE =================

conn = sqlite3.connect("carnivale_pro.db", check_same_thread=False)
c = conn.cursor()

# Tables
c.execute("""CREATE TABLE IF NOT EXISTS branches(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT UNIQUE
)""")

c.execute("""CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT UNIQUE,
password TEXT,
role TEXT,
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
feedback_id TEXT,
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

# ================= SESSION =================

if "login" not in st.session_state:
    st.session_state.login = False

# ================= LOGIN =================

def login():
    st.title("🎭 CARNIVALE PRO LOGIN")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        result = pd.read_sql("SELECT * FROM users WHERE username=? AND password=?",
                             conn, params=(user, pwd))
        if not result.empty:
            st.session_state.login = True
            st.session_state.username = user
            st.session_state.role = result.iloc[0]["role"]
            st.session_state.branch = result.iloc[0]["branch"]
            st.success("Login Successful")
            st.rerun()
        else:
            st.error("Invalid Credentials")

# ================= PERMISSION MATRIX =================

def check_permission(role, action):
    permissions = {
        "admin": ["add_branch","add_user","view_all","feedback","analytics"],
        "staff": ["feedback","view_branch"]
    }
    return action in permissions.get(role, [])

# ================= UI HEADER =================

def header():
    st.markdown("""
    <h1 style='text-align:center;color:#D4AF37;'>🎭 CARNIVALE PRO ENTERPRISE</h1>
    """, unsafe_allow_html=True)

# ================= MAIN APP =================

def main():
    header()

    role = st.session_state.role
    branch = st.session_state.branch

    menu = st.sidebar.selectbox("Menu",
    ["Dashboard","Guest Entry","Feedback Form","Analytics","Admin Panel","Logout"])

    # DASHBOARD
    if menu=="Dashboard":
        st.subheader("📊 Branch Dashboard")

        if role=="admin":
            data = pd.read_sql("SELECT * FROM guests",conn)
        else:
            data = pd.read_sql("SELECT * FROM guests WHERE branch=?",
                               conn, params=(branch,))

        st.metric("Total Guests",len(data))

    # GUEST ENTRY
    if menu=="Guest Entry":
        st.subheader("📝 Guest Entry")

        branches = pd.read_sql("SELECT name FROM branches",conn)

        if role=="staff":
            selected_branch = branch
        else:
            selected_branch = st.selectbox("Branch",branches["name"])

        name = st.text_input("Guest Name")
        mobile = st.text_input("Mobile")

        if st.button("Submit Entry"):
            c.execute("INSERT INTO guests(name,mobile,branch,staff,date) VALUES(?,?,?,?,?)",
                      (name,mobile,selected_branch,
                       st.session_state.username,str(datetime.now())))
            conn.commit()
            st.success("Guest Added")

    # FEEDBACK
    if menu=="Feedback Form":
        st.subheader("⭐ Premium Feedback")

        if role=="staff":
            guests = pd.read_sql("SELECT * FROM guests WHERE branch=?",
                                 conn, params=(branch,))
        else:
            guests = pd.read_sql("SELECT * FROM guests",conn)

        if not guests.empty:
            guest_select = st.selectbox("Select Guest",
                                        guests["name"]+" - "+guests["mobile"])

            # Duplicate check
            selected_mobile = guest_select.split(" - ")[1]
            dup = pd.read_sql("SELECT * FROM feedback f JOIN guests g ON f.guest_id=g.id WHERE g.mobile=?",
                              conn, params=(selected_mobile,))

            if not dup.empty:
                st.warning("⚠ Feedback Already Submitted For This Guest")

            food = st.slider("🍽 Food",1,5)
            service = st.slider("🤵 Service",1,5)
            behaviour = st.slider("🙂 Behaviour",1,5)
            ambience = st.slider("🏨 Ambience",1,5)
            cleanliness = st.slider("🧹 Cleanliness",1,5)
            comment = st.text_area("Comment")

            if st.button("Submit Feedback"):
                guest_id = guests.iloc[
                    guests["name"]+" - "+guests["mobile"]==guest_select].id.values[0]

                feedback_id = "FDBK-"+str(uuid.uuid4())[:8]

                c.execute("""INSERT INTO feedback
                (feedback_id,guest_id,food,service,behaviour,ambience,cleanliness,comment,date)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (feedback_id,guest_id,food,service,behaviour,ambience,cleanliness,comment,str(datetime.now())))
                conn.commit()

                st.success(f"Feedback Submitted 🎉 ID: {feedback_id}")
                st.balloons()

    # ANALYTICS
    if menu=="Analytics":
        st.subheader("📈 Growth Analytics")

        data = pd.read_sql("""
        SELECT date, COUNT(id) as entries
        FROM guests GROUP BY date
        """,conn)

        if not data.empty:
            fig = px.line(data,x="date",y="entries",title="Daily Growth")
            st.plotly_chart(fig)

    # ADMIN PANEL
    if menu=="Admin Panel" and role=="admin":
        st.subheader("👑 Admin Controls")

        new_branch = st.text_input("Add Branch")
        if st.button("Create Branch"):
            c.execute("INSERT INTO branches(name) VALUES(?)",(new_branch,))
            conn.commit()
            st.success("Branch Added")

        st.markdown("---")
        st.subheader("Add User")

        uname = st.text_input("Username")
        pwd = st.text_input("Password")
        role_new = st.selectbox("Role",["admin","staff"])
        branch_new = st.text_input("Branch (For Staff)")

        if st.button("Create User"):
            c.execute("INSERT INTO users(username,password,role,branch) VALUES(?,?,?,?)",
                      (uname,pwd,role_new,branch_new))
            conn.commit()
            st.success("User Created")

    if menu=="Logout":
        st.session_state.login=False
        st.rerun()

# ================= APP FLOW =================

if not st.session_state.login:
    login()
else:
    main()
    if menu=="Analytics":
        st.subheader("📈 Growth Analytics Intelligence")

        guests_df = pd.read_sql("SELECT * FROM guests",conn)
        feedback_df = pd.read_sql("""
        SELECT f.*, g.staff, g.branch, g.mobile
        FROM feedback f
        JOIN guests g ON f.guest_id=g.id
        """,conn)

        if role=="staff":
            guests_df = guests_df[guests_df["branch"]==branch]
            feedback_df = feedback_df[feedback_df["branch"]==branch]

        # Daily Growth
        guests_df["date_only"] = pd.to_datetime(guests_df["date"]).dt.date
        daily = guests_df.groupby("date_only").size().reset_index(name="entries")

        if not daily.empty:
            fig = px.line(daily,x="date_only",y="entries",title="Daily Guest Growth")
            st.plotly_chart(fig)

        # Monthly Growth
        guests_df["month"] = pd.to_datetime(guests_df["date"]).dt.to_period("M").astype(str)
        monthly = guests_df.groupby("month").size().reset_index(name="entries")

        if not monthly.empty:
            fig2 = px.bar(monthly,x="month",y="entries",title="Monthly Growth")
            st.plotly_chart(fig2)

        st.markdown("### 🔁 Repeat Customer Intelligence")

        repeat = guests_df.groupby("mobile").size().reset_index(name="visits")
        repeat = repeat[repeat["visits"]>1]

        if not repeat.empty:
            repeat_detail = pd.merge(repeat,guests_df,on="mobile")
            st.dataframe(repeat_detail[["name","mobile","branch","staff","visits"]])
        else:
            st.info("No Repeat Guests Yet")

        st.markdown("### 🚨 Multi Feedback Alert")

        multi_feedback = feedback_df.groupby("mobile").size().reset_index(name="feedback_count")
        multi_feedback = multi_feedback[multi_feedback["feedback_count"]>1]

        if not multi_feedback.empty:
            st.warning("Multiple feedback submitted by same mobile")
            st.dataframe(multi_feedback)
        else:
            st.success("No Multiple Feedback Detected")

        st.markdown("### 🕵 Backdate Fraud Detection")

        fraud = guests_df[pd.to_datetime(guests_df["date"]) < pd.Timestamp.now() - pd.Timedelta(days=30)]
        if not fraud.empty:
            st.error("Old Backdated Entries Found")
            st.dataframe(fraud[["name","mobile","date","staff"]])
        else:
            st.success("No Backdated Fraud Detected")
menu = st.sidebar.selectbox("Menu",
["Dashboard","Guest Entry","Feedback Form","Analytics","Performance & Salary","Admin Panel","Logout"])
    if menu=="Performance & Salary":
        st.subheader("💰 Staff Performance Intelligence")

        df = pd.read_sql("""
        SELECT g.staff,
        COUNT(f.id) as total_feedback,
        AVG((f.food+f.service+f.behaviour+f.ambience+f.cleanliness)/5.0) as avg_rating
        FROM feedback f
        JOIN guests g ON f.guest_id=g.id
        GROUP BY g.staff
        """,conn)

        if role=="staff":
            df = df[df["staff"]==st.session_state.username]

        if not df.empty:
            # Advanced Salary Formula
            base_salary = 10000
            df["rating_bonus"] = df["avg_rating"]*2000
            df["volume_bonus"] = df["total_feedback"]*50
            df["final_salary"] = base_salary + df["rating_bonus"] + df["volume_bonus"]

            st.dataframe(df)

            st.markdown("### 📊 Performance Chart")
            fig = px.bar(df,x="staff",y="final_salary",title="Salary Comparison")
            st.plotly_chart(fig)

        else:
            st.info("No Feedback Data Yet")
menu = st.sidebar.selectbox("Menu",
["Dashboard","Guest Entry","Feedback Form","Analytics",
"Performance & Salary","Automation Center",
"Admin Panel","Logout"])
    if menu=="Automation Center":
        st.subheader("🤖 Automation Center")

        role = st.session_state.role

        if role!="admin":
            st.error("Permission Denied")
            st.stop()

        data = pd.read_sql("""
        SELECT g.name,g.mobile,g.branch,g.staff,f.comment,f.date
        FROM feedback f
        JOIN guests g ON f.guest_id=g.id
        """,conn)

        if data.empty:
            st.info("No Data Available")
        else:

            # ================= PDF EXPORT =================
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import pagesizes

            if st.button("Generate PDF Report"):
                file="carnivale_report.pdf"
                doc = SimpleDocTemplate(file,pagesize=pagesizes.A4)
                elements=[]
                styles=getSampleStyleSheet()
                elements.append(Paragraph("CARNIVALE ENTERPRISE REPORT",styles["Title"]))
                elements.append(Spacer(1,12))
                table_data=[list(data.columns)]+data.values.tolist()
                t=Table(table_data)
                t.setStyle([('BACKGROUND',(0,0),(-1,0),colors.gold),
                            ('GRID',(0,0),(-1,-1),1,colors.black)])
                elements.append(t)
                doc.build(elements)

                with open(file,"rb") as f:
                    st.download_button("Download PDF",f,file)

            # ================= EXCEL EXPORT =================
            if st.button("Export Excel"):
                excel_file="carnivale_report.xlsx"
                data.to_excel(excel_file,index=False)
                with open(excel_file,"rb") as f:
                    st.download_button("Download Excel",f,excel_file)

            # ================= EMAIL AUTO SEND =================
            import smtplib
            from email.mime.text import MIMEText

            email_to = st.text_input("Send Report To Email")

            if st.button("Send Email Report"):
                try:
                    msg = MIMEText("CARNIVALE Report Attached.")
                    msg["Subject"]="CARNIVALE Enterprise Report"
                    msg["From"]=st.secrets["EMAIL_USER"]
                    msg["To"]=email_to

                    server = smtplib.SMTP("smtp.gmail.com",587)
                    server.starttls()
                    server.login(st.secrets["EMAIL_USER"],st.secrets["EMAIL_PASS"])
                    server.sendmail(msg["From"],[email_to],msg.as_string())
                    server.quit()

                    st.success("Email Sent Successfully")

                except Exception as e:
                    st.error("Email Failed")

            # ================= WHATSAPP AUTO SEND =================
            from twilio.rest import Client

            phone = st.text_input("Send WhatsApp To (with country code)")

            if st.button("Send WhatsApp Notification"):
                try:
                    client = Client(st.secrets["TWILIO_SID"],st.secrets["TWILIO_AUTH"])
                    client.messages.create(
                        body="CARNIVALE Report Generated Successfully",
                        from_=st.secrets["TWILIO_NUMBER"],
                        to="whatsapp:"+phone
                    )
                    st.success("WhatsApp Sent")

                except:
                    st.error("WhatsApp Failed")
st.toast("Notification: New Feedback Received 🚀")
st.markdown("""
<style>
.card {
    background-color: #1e1e1e;
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0 0 15px rgba(212,175,55,0.5);
    margin-bottom: 20px;
}
.gold {
    color: #D4AF37;
    font-weight: bold;
}
.stButton>button {
    border-radius: 10px;
    background-color: #D4AF37;
    color: black;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)
if menu=="Dashboard":
    st.subheader("📊 Branch Dashboard")

    if role=="admin":
        data = pd.read_sql("SELECT * FROM guests",conn)
    else:
        data = pd.read_sql("SELECT * FROM guests WHERE branch=?",
                           conn, params=(branch,))

    col1,col2 = st.columns(2)

    with col1:
        st.markdown(f"<div class='card'><h2 class='gold'>Total Guests</h2><h1>{len(data)}</h1></div>",unsafe_allow_html=True)

    feedback_count = pd.read_sql("SELECT COUNT(*) as c FROM feedback",conn)["c"][0]

    with col2:
        st.markdown(f"<div class='card'><h2 class='gold'>Total Feedback</h2><h1>{feedback_count}</h1></div>",unsafe_allow_html=True)
def emoji_rating(label):
    st.markdown(f"### {label}")
    rating = st.radio(
        "",
        ["😡 1","😕 2","😐 3","🙂 4","😍 5"],
        horizontal=True,
        key=label
    )
    return int(rating.split()[1])
food = emoji_rating("🍽 Food")
service = emoji_rating("🤵 Service")
behaviour = emoji_rating("🙂 Behaviour")
ambience = emoji_rating("🏨 Ambience")
cleanliness = emoji_rating("🧹 Cleanliness")
st.success(f"Feedback Submitted 🎉 ID: {feedback_id}")
st.balloons()

st.markdown("""
<div class='card'>
<h2 class='gold'>🙏 Thank You For Your Valuable Feedback</h2>
<p>Your response helps CARNIVALE grow better every day.</p>
</div>
""",unsafe_allow_html=True)
def check_permission(role, action):
    permissions = {
        "admin": ["all"],
        "staff": ["guest_entry","feedback","dashboard","performance"]
    }

    if "all" in permissions.get(role,[]):
        return True

    return action in permissions.get(role,[])
if not check_permission(role,"guest_entry"):
    st.error("Access Denied")
    st.stop()
if role=="staff":
    st.info("You can only add entries for your branch.")
if role=="admin":
    branch_filter = st.selectbox("Filter By Branch",
                                 ["All"] + list(pd.read_sql("SELECT name FROM branches",conn)["name"]))

    if branch_filter!="All":
        guests_df = guests_df[guests_df["branch"]==branch_filter]
        feedback_df = feedback_df[feedback_df["branch"]==branch_filter]

