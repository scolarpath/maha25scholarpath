from flask import Flask, render_template, request, redirect, session
import sqlite3
import random
import re
import time
import os
import logging
import smtplib
from email.mime.text import MIMEText
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import pandas as pd


# ---------------- APP ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret")

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)

# ---------------- DB ----------------
def get_db():
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect("data.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()
# ---------------- OTP STORAGE ----------------
otp_storage = {}
OTP_EXPIRY = 300

# ---------------- EMAIL CONFIG ----------------
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

# ---------------- VALID EMAIL ----------------
def valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

# ---------------- HOME ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/home")
def home():
    return render_template("home.html")

@app.route("/information")
def information():
    return render_template("information.html")

# ---------------- LANGUAGE ----------------
@app.route("/set_language/<lang>")
def set_language(lang):
    session["language"] = lang
    return redirect(request.referrer or "/")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
    user = cur.fetchone()

    if user:
        session["user"] = email
        return redirect("/information")

    return "Invalid login"

# ---------------- REGISTER ----------------
@app.route("/register", methods=["POST"])
def register():

    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")
    otp = request.form.get("otp")

    if not name or not email or not password or not otp:
        return "Missing fields"

    email = email.strip().lower()

    data = otp_storage.get(email)

    if not data:
        return "Please request OTP first"

    if data["otp"] != otp.strip():
        return "Invalid OTP"

    conn = sqlite3.connect("data.db")
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO users(name,email,password) VALUES (?,?,?)",
        (name, email, password)
    )

    conn.commit()
    conn.close()

    otp_storage.pop(email, None)

    return redirect("/home")
# ---------------- SEND OTP ----------------
@app.route("/send_otp", methods=["POST"])
def send_otp():

    email = request.form.get("email")

    if not email:
        return "Email required"

    email = email.strip().lower()

    otp = str(random.randint(100000, 999999))

    otp_storage[email] = {
        "otp": otp,
        "time": time.time()
    }

    try:
        message = Mail(
            from_email="maha25scholarpath.noreply@gmail.com",
            to_emails=email,
            subject="OTP Verification",
            plain_text_content=f"Your OTP is: {otp}"
        )

        sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
        sg.send(message)

        print("OTP SENT")

        return "OTP sent successfully"

    except Exception as e:
        print("SENDGRID ERROR:", repr(e))
        return "Failed to send OTP"
# ---------------- VERIFY OTP ----------------
@app.route("/verify_otp", methods=["POST"])
def verify_otp():

    email = request.form.get("email")
    otp = request.form.get("otp")

    if not email or not otp:
        return "Missing fields"

    email = email.strip().lower()
    otp = otp.strip()

    data = otp_storage.get(email)

    if not data:
        return "OTP expired or not found"

    if time.time() - data["time"] > 300:
        otp_storage.pop(email, None)
        return "OTP expired"

    if data["otp"] == otp:
        session["verified"] = True
        return redirect("/home")

    return "Invalid OTP"
# ---------------- SEARCH ----------------
@app.route("/search", methods=["POST"])
def search():

    caste = request.form["caste"].lower()
    gender = request.form["gender"].lower()
    income = int(request.form["income"])
    age = int(request.form["age"])

    if age > 25:
        return render_template(
            "output.html",
            schemes=[],
            message="Only users aged 25 or below allowed"
        )

    df = pd.read_csv("dataset.csv")

    eligible = []

    for _, row in df.iterrows():

        try:

            scheme_caste = str(row["caste"]).lower()
            scheme_gender = str(row["gender"]).lower()
            scheme_income = int(row["annual_income"])

            if (
                scheme_caste in [caste, "all"] and
                scheme_gender in [gender, "all", "any"] and
                income <= scheme_income
            ):

                eligible.append({
                    "name": row["name_of_scheme"],
                    "gender": row["gender"],
                    "caste": row["caste"],
                    "income": row["annual_income"],
                    "education": row["educational_qualification"],
                    "link": row["link"],
                    "documents": row["required_documents"]
                })

        except:
            pass

    return render_template("output.html", schemes=eligible)

# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()

    port = int(os.environ.get("PORT", 5000))

    app.run(host="0.0.0.0", port=port)
