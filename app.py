# Replace your current `app.py` important sections with the following updated code.


from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
import random
import re
import sqlite3
import pandas as pd
import logging
import smtplib

from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------------- LOAD DATASET ----------------

df = pd.read_excel("dataset.xlsx")

# ---------------- LOGGING ----------------

logging.basicConfig(
    filename="email_reminders.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

email_logger = logging.getLogger("email_logger")
email_logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("reminder_logs.txt")
formatter = logging.Formatter("%(asctime)s - %(message)s")
file_handler.setFormatter(formatter)
email_logger.addHandler(file_handler)

# ---------------- FLASK APP ----------------

app = Flask(__name__)
app.secret_key = "Maha25ScholarPathSecureKey"

# ---------------- SQLITE DATABASE ----------------

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT
)
""")

conn.commit()

# ---------------- EMAIL CONFIG ----------------

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'maha25scholarpath.noreply@gmail.com'
app.config['MAIL_PASSWORD'] = 'nzee dymu qfmw domm'
app.config['MAIL_DEFAULT_SENDER'] = 'maha25scholarpath.noreply@gmail.com'

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
    pattern = r'^[\w.-]+@[\w.-]+\.\w+$'
    return re.match(pattern, email)

# ---------------- DATABASE FUNCTIONS ----------------


def get_users_with_upcoming_deadlines():

    cursor.execute("SELECT id, name, email FROM users")
    rows = cursor.fetchall()

    users = []

    for row in rows:
        users.append({
            "id": row[0],
            "name": row[1],
            "email": row[2]
        })

    return users


def get_user_deadlines(user_id):

    deadlines = {}

    try:
        for _, row in df.iterrows():

            if "deadline" in row and pd.notna(row["deadline"]):
                deadlines[row["name_of_scheme"]] = str(row["deadline"])

    except Exception as e:
        print("Deadline Error:", e)

    return deadlines

# ---------------- EMAIL REMINDER ----------------


def send_deadline_email(to_email, deadlines, user_name="User"):

    sender_email = "maha25scholarpath.noreply@gmail.com"
    sender_password = "nzee dymu qfmw domm"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = "Upcoming Scheme Deadlines"

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

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)

        logging.info(f"Email sent to {to_email}")

    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {e}")

# ---------------- REMINDER ROUTE ----------------


@app.route("/send_reminders")
def send_reminders():

    today = datetime.today()

    users = get_users_with_upcoming_deadlines()

    for user in users:

        deadlines = get_user_deadlines(user["id"])

        upcoming = {
            scheme: date
            for scheme, date in deadlines.items()
            if datetime.strptime(date.split()[0], "%Y-%m-%d") <= today + timedelta(days=7)
        }

        if upcoming:
            try:
                send_deadline_email(user["email"], upcoming, user["name"])

            except Exception as e:
                email_logger.error(f"Failed to send email: {e}")

    return "Reminder emails sent!"

# ---------------- SCHEDULER ----------------

scheduler = BackgroundScheduler()
scheduler.add_job(func=send_reminders, trigger="interval", hours=24)
scheduler.start()

# ---------------- LANGUAGE ----------------


@app.route("/set_language/<lang>")
def set_language(lang):
    session["language"] = lang
    return redirect(request.referrer)

# ---------------- PAGES ----------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/home")
def home():
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/information")
def information():
    return render_template("information.html")

# ---------------- REGISTER ----------------


@app.route("/register", methods=["POST"])
def register():

    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    otp = request.form["otp"]

    if otp_storage.get(email) != otp:
        return "Invalid OTP"

    cursor.execute(
        "INSERT INTO users (name, email, password) VALUES (?,?,?)",
        (name, email, password)
    )

    conn.commit()

    return redirect("/home")

# ---------------- LOGIN ----------------


@app.route("/login", methods=["POST"])
def login():

    email = request.form["email"].strip()
    password = request.form["password"].strip()

    cursor.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, password)
    )

    user = cursor.fetchone()

    if user:
        session["user"] = email
        return redirect("/information")

    else:
        return "Invalid email or password"

# ---------------- ADMIN ----------------


@app.route("/admin", methods=["GET", "POST"])
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

    schemes = df.values.tolist()

    return render_template("admin_dashboard.html", schemes=schemes)

# ---------------- OTP ----------------


@app.route("/send_otp", methods=["GET", "POST"])
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

# ---------------- SEARCH ----------------

current_date = datetime.today().date()


@app.route("/search", methods=["POST"])
def search():

    caste = request.form["caste"].lower()
    gender = request.form["gender"].lower()
    income = int(request.form["income"])
    education = request.form["education"]
    age = int(request.form["age"])

    if caste == "general":
        caste = "open"

    if age > 25:

        if session.get("language") == "mr":
            msg = "ही वेबसाइट फक्त २५ वर्षे किंवा त्याखालील वयाच्या वापरकर्त्यांसाठी उपलब्ध आहे."

        else:
            msg = "This website is applicable only for users aged 25 or below."

        return render_template("output.html", schemes=[], message=msg)

    user_level = education_levels.get(education, 0)

    schemes = df.values.tolist()

    eligible_schemes = []

    for scheme in schemes:

        try:
            scheme_gender = str(scheme[2]).lower()
            scheme_caste = str(scheme[3]).lower()
            scheme_income = int(scheme[4])
            scheme_education = scheme[5]
            scheme_level = education_levels.get(scheme_education, 0)

            if (
                (scheme_caste == caste or scheme_caste in ["all"]) and
                (scheme_gender == gender or scheme_gender in ["all", "any"]) and
                income <= scheme_income and
                user_level >= scheme_level
            ):
                eligible_schemes.append(scheme)

        except:
            pass

    return render_template(
        "output.html",
        schemes=eligible_schemes,
        current_date=current_date,
        message=None
    )

# ---------------- RUN APP ----------------


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)



