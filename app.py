from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
#import mysql.connector
import random
import re
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd

df = pd.read_excel("dataset.xlsx")

logging.basicConfig(
    filename="email_reminders.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s")

email_logger = logging.getLogger("email_logger")
email_logger.setLevel(logging.INFO)

# Create a file handler that writes ONLY to reminder_logs.txt
file_handler = logging.FileHandler("reminder_logs.txt")
formatter = logging.Formatter("%(asctime)s - %(message)s")
file_handler.setFormatter(formatter)

# Add the handler to the logger
email_logger.addHandler(file_handler)



app = Flask(__name__)
app.secret_key = "Maha25ScholarPathSecureKey"


# Step 1: Database placeholder functions
def get_users_with_upcoming_deadlines():
    cursor = db.cursor()
    #cursor.execute("SELECT id, name, email FROM users")
    #rows = cursor.fetchall()
    results = df.to_dict(orient="records")
    # Convert to list of dicts
    users = [{"id": row[0], "name": row[1], "email": row[2]} for row in rows]
    cursor.close()
    return users

def get_user_deadlines(user_id):
    cursor = db.cursor()
    cursor.execute(
        "SELECT name_of_scheme, deadline FROM schemes WHERE id = %s", (user_id,)
        )
    rows = cursor.fetchall()
    deadlines = {row[0]: row[1] for row in rows}
    cursor.close()
    return deadlines

def send_deadline_email(to_email, deadlines, user_name="User"):
    sender_email = "maha25scholarpath.noreply@gmail.com"
    sender_password = "nzee dymu qfmw domm"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = "Upcoming Scheme Deadlines"

    # Step 5: HTML body with personalization
    body = f"""
    <html>
    <body>
    <p>Hello {user_name},</p>
    <p>Here are your upcoming deadlines:</p>
    <ul>
    """
    for scheme, date in deadlines.items():
        body += f"<li>{scheme}: {date}</li>"
    body += "</ul></body></html>"

    message.attach(MIMEText(body, "html"))

    # Send email
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        logging.info(f"Email sent to {to_email} for deadlines: {list(deadlines.keys())}")
    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {e}")

# ---------------- DATABASE CONNECTION ----------------

#db = mysql.connector.connect(
#host="localhost",
#user="root",
#password="",
#database="maha25scholarpath"
#)

#cursor = db.cursor()

# ---------------- EMAIL CONFIG ----------------

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'maha25scholarpath.noreply@gmail.com'
app.config['MAIL_DEFAULT_SENDER'] = 'maha25scholarpath.noreply@gmail.com'
app.config['MAIL_PASSWORD'] = 'nzee dymu qfmw domm'
app.config['MAIL_DEFAULT_SENDER'] = '[maha25scholarpath.noreply@gmail.com](mailto:maha25scholarpath.noreply@gmail.com)'

mail = Mail(app)

# ---------------- OTP STORAGE ----------------

otp_storage = {}

# ---------------- EDUCATION LEVELS ----------------

education_levels = {
"10th": 1,
"12th": 2,
"Graduate": 3,
"Post-Graduate": 4
}

# ---------------- EMAIL VALIDATION ----------------

def valid_email(email):
 pattern = r'^[\w.-]+@[\w.-]+.\w+$'
 return re.match(pattern, email)

# ---------------- LANGUAGE ----------------

@app.route("/set_language/<lang>")
def set_language(lang):
 session["language"] = lang
 return redirect(request.referrer)





# Configure logging


@app.route("/send_reminders")
def send_reminders():
    today = datetime.today()
    
    # Step 1: fetch users from your database
    users = get_users_with_upcoming_deadlines()  # Replace with your DB function

    for user in users:
        deadlines = get_user_deadlines(user["id"])  # Replace with your DB function

        # Step 2: filter only upcoming deadlines
        upcoming = {scheme: date for scheme, date in deadlines.items()
                    if datetime.strptime(date, "%Y-%m-%d") <= today + timedelta(days=7)}

        if upcoming:
            # Step 6: error handling
            try:
                send_deadline_email(user["email"], upcoming, user["name"])
                # Use the separate logger
               
            except Exception as e:
                email_logger.error(f"Failed to send email to {user['email']}: {e}")

    return "Reminder emails sent!"

# Step 4: Set up scheduler once when app starts
scheduler = BackgroundScheduler()
scheduler.add_job(func=send_reminders, trigger="interval", hours=24)
scheduler.start()


# ---------------- PAGES ----------------
@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/")
def index():
 return render_template("index.html")

@app.route("/home")
def home():
 return render_template("home.html")

@app.route("/information")
def information():
    return render_template("information.html")

@app.route("/register", methods=["POST"])
def register():

    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    otp = request.form["otp"]

    # check OTP
    if otp_storage.get(email) != otp:
        return "Invalid OTP"

    # insert user in database
    cursor.execute(
        "INSERT INTO users (name, email, password) VALUES (%s,%s,%s)",
        (name, email, password)
    )
    db.commit()

    return redirect("/home")

@app.route("/login", methods=["POST"])
def login():

    email = request.form["email"].strip()
    password = request.form["password"].strip()

    cursor.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (email, password)
    )

    user = cursor.fetchone()
    print("USER FOUND:", user)


    if user:
        session["user"] = email
        return redirect("/information")
    else:
        return "Invalid email or password"
    

@app.route("/admin", methods=["GET","POST"])
def admin():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect("/admin_dashboard")
        else:
            return "Invalid Admin Login"

    return render_template("admin_login.html")

@app.route("/admin_dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect("/admin")

    cursor.execute("SELECT * FROM schemes")
    schemes = cursor.fetchall()

    return render_template("admin_dashboard.html", schemes=schemes)

@app.route("/add_scheme", methods=["POST"])
def add_scheme():

    if "admin" not in session:
        return redirect("/admin")

    name = request.form["name"]
    gender = request.form["gender"]
    caste = request.form["caste"]
    income = request.form["income"]
    education = request.form["education"]
    documents = request.form["documents"]
    link = request.form["link"]

    cursor.execute(
        "INSERT INTO schemes (name,gender,caste,income,education,documents,link) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (name, gender, caste, income, education, documents, link)
    )

    db.commit()

    return redirect("/admin_dashboard")

@app.route("/delete_scheme/<int:id>")
def delete_scheme(id):

    if "admin" not in session:
        return redirect("/admin")

    cursor.execute("DELETE FROM schemes WHERE id=%s", (id,))
    db.commit()

    return redirect("/admin_dashboard")

@app.route("/admin_logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin")

@app.route("/edit_scheme/<int:id>")
def edit_scheme(id):

    if "admin" not in session:
        return redirect("/admin")

    cursor.execute("SELECT * FROM schemes WHERE id=%s", (id,))
    scheme = cursor.fetchone()

    return render_template("edit_scheme.html", scheme=scheme)

@app.route("/update_scheme", methods=["POST"])
def update_scheme():

    if "admin" not in session:
        return redirect("/admin")

    id = request.form["id"]
    name = request.form["name"]
    gender = request.form["gender"]
    caste = request.form["caste"]
    income = request.form["income"]
    education = request.form["education"]

    cursor.execute(
        """UPDATE schemes
        SET scheme_name=%s, gender=%s, caste=%s, income=%s, education=%s
        WHERE id=%s""",
        (name, gender, caste, income, education, id)
    )

    db.commit()

    return redirect("/admin_dashboard")

# ---------------- SEND OTP ----------------




@app.route("/send_otp", methods=["GET","POST"])
def send_otp():

    email = request.form.get("email")

    if not valid_email(email):
        return "Invalid email format"

    otp = str(random.randint(100000, 999999))
    otp_storage[email] = otp

    try:
        msg = Message(
            subject="Maha25 ScholarPath Email Verification",
            recipients=[email]
        )

        msg.body = "Your OTP for email verification is: " + otp

        mail.send(msg)

        return render_template("verify.html", email=email)

    except Exception as e:
        print("Mail error:", e)
        return "Failed to send OTP"


# ---------------- VERIFY OTP ----------------

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
 email = request.form.get("email")
 user_otp = request.form.get("otp")

 if otp_storage.get(email) == user_otp:
    session["verified_email"] = email
    return redirect("/home")
 else:
    return "Invalid OTP"

@app.route("/create_account", methods=["POST"])
def create_account():

    email = request.form["email"]
    password = request.form["password"]

    cursor.execute(
        "INSERT INTO users (email, password) VALUES (%s,%s)",
        (email, password)
    )

    db.commit()

    return redirect("/home")
# ---------------- SEARCH SCHEMES ----------------

from datetime import datetime
current_date = datetime.today().date()

@app.route("/search", methods=["POST"])
def search():
    
    caste = request.form["caste"].lower()
    gender = request.form["gender"].lower()
    income = int(request.form["income"])
    education = request.form["education"]
    age = int(request.form["age"])
    notify = request.form.get("notify")
    email = session.get("email")

    if caste == "general":
        caste = "open"

    if age > 25:
        if session.get("language") == "mr":
            msg = "ही वेबसाइट फक्त २५ वर्षे किंवा त्याखालील वयाच्या वापरकर्त्यांसाठी उपलब्ध आहे."
        else:
            msg = "This website is applicable only for users aged 25 or below."
        return render_template("output.html", schemes=[], message=msg)

    user_level = education_levels.get(education, 0)

    cursor.execute("SELECT * FROM schemes")
    schemes = cursor.fetchall()

    eligible_schemes = []
    notifications = []

    for scheme in schemes:
        scheme_gender = scheme[2].lower()
        scheme_caste = scheme[3].lower()
        scheme_income = int(scheme[4])
        scheme_education = scheme[5]
        scheme_level = education_levels.get(scheme_education, 0)
        scheme_deadline = scheme[8]

        days_left = None

        if scheme_deadline:
         today = datetime.today().date()
         diff = (scheme_deadline - today).days

         if diff >= 0:
            days_left = diff

        status = "open"
        if scheme_deadline and scheme_deadline < datetime.today().date():
          status = "closed"

        if (scheme_caste == caste or scheme_caste in ["all"]) and \
           (scheme_gender == gender or scheme_gender in ["all", "any"]) and \
           income <= scheme_income and \
           user_level >= scheme_level:

           scheme = list(scheme)

           if scheme_deadline and scheme_deadline < current_date:
            scheme.append("closed")
           else:
            scheme.append("open")

           eligible_schemes.append((scheme, days_left, status))

        # 🔔 Notification logic
           if notify and days_left is not None and days_left <= 5:
            notifications.append({
                "name": scheme[1],
                "days": days_left,
                "link": scheme[7]
            })

        if notify and email and notifications:
         print("Sending email to:", email)

         message_text = "Upcoming Scheme Deadlines:\n\n"

         for n in notifications:
          message_text += f"{n['name']} - Deadline in {n['days']} days\n"

         msg = Message(
         subject="Scholarship Deadline Alert",
         sender="your_email@gmail.com",
         recipients=[email]
         )

         msg.body = message_text
         mail.send(msg)
    

        
    # <-- RETURN OUTSIDE ALL LOOPS
    
    return render_template(
    "output.html",
    schemes=eligible_schemes,
    notifications=notifications,
    current_date=current_date,
    message=None
)


# ---------------- RUN APP ----------------

if __name__ == "__main__":
 app.run(debug=True)
