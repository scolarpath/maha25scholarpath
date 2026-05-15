from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
import random
import re
import sqlite3
import pandas as pd
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------------- APP ----------------

app = Flask(__name__)
app.secret_key = "Maha25ScholarPathSecureKey"

# ---------------- DATA (CRASH SAFE FIX) ----------------
# Load ONCE, reduce memory usage

df = pd.read_csv(
    "dataset.csv",
    low_memory=True,
    dtype=str
).fillna("")

# ---------------- LOGGING ----------------

logging.basicConfig(
    filename="email_reminders.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

# ---------------- SQLITE ----------------

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

# ---------------- MAIL ----------------

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'maha25scholarpath.noreply@gmail.com'
app.config['MAIL_PASSWORD'] = 'nzee dymu qfmw domm'
app.config['MAIL_DEFAULT_SENDER'] = 'maha25scholarpath.noreply@gmail.com'

mail = Mail(app)

# ---------------- OTP ----------------

otp_storage = {}

def valid_email(email):
    return re.match(r'^[\w.-]+@[\w.-]+\.\w+$', email)

# ---------------- HOME ----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/home")
def home():
    return render_template("home.html")

# ---------------- OTP SEND (SAFE) ----------------

@app.route("/send_otp", methods=["POST"])
def send_otp():
    email = request.form.get("email")

    if not valid_email(email):
        return "Invalid email format"

    otp = str(random.randint(100000, 999999))
    otp_storage[email] = otp

    msg = Message(
        subject="Maha25 ScholarPath OTP",
        recipients=[email],
        body=f"Your OTP is: {otp}"
    )

    try:
        mail.send(msg)
        return render_template("verify.html", email=email)
    except Exception as e:
        print("Mail error:", e)
        return "OTP sending failed"

# ---------------- VERIFY OTP ----------------

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    email = request.form.get("email")
    user_otp = request.form.get("otp")

    if otp_storage.get(email) == user_otp:
        session["verified_email"] = email
        return redirect("/home")

    return "Invalid OTP"

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
        return redirect("/home")

    return "Invalid login"

# ---------------- EDUCATION LEVELS ----------------

education_levels = {
    "10th": 1,
    "12th": 2,
    "Graduate": 3,
    "Post-Graduate": 4
}

# ---------------- SEARCH (SAFE, NO CRASH) ----------------

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
        return render_template(
            "output.html",
            schemes=[],
            message="Only users aged 25 or below allowed"
        )

    eligible = []

    try:
        for _, s in df.iterrows():

            scheme_gender = str(s[2]).lower()
            scheme_caste = str(s[3]).lower()

            try:
                scheme_income = int(s[4])
            except:
                scheme_income = 0

            scheme_edu = str(s[5])
            scheme_level = education_levels.get(scheme_edu, 0)

            if (
                (scheme_caste in [caste, "all"]) and
                (scheme_gender in [gender, "all", "any"]) and
                income <= scheme_income and
                education_levels.get(education, 0) >= scheme_level
            ):
                eligible.append(list(s))

    except Exception as e:
        print("Search error:", e)

    return render_template("output.html", schemes=eligible)

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
