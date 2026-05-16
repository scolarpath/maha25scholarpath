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
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    otp = request.form["otp"]

    if email not in otp_storage:
        return "OTP not found"

    if otp_storage[email]["otp"] != otp:
        return "Invalid OTP"

    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO users(name,email,password) VALUES (?,?,?)",
                (name, email, password))
    db.commit()

    otp_storage.pop(email, None)

    return redirect("/home")

# ---------------- SEND OTP ----------------
@app.route("/send_otp", methods=["POST"])
def send_otp():
    email = request.form.get("email")

    if not email:
        return "Email required"

    otp = str(random.randint(100000, 999999))

    otp_storage[email] = {
        "otp": otp,
        "time": time.time()
    }

    try:
        message = Mail(
            from_email="maha25scholarpath.noreply@gmail.com",  # must be VERIFIED in SendGrid
            to_emails=email,
            subject="OTP Verification - Maha25 ScholarPath",
            plain_text_content=f"Your OTP is: {otp}"
        )

        sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
        response = sg.send(message)

        print("SENDGRID STATUS:", response.status_code)

        return "OTP sent successfully"

    except Exception as e:
        print("SENDGRID FULL ERROR:", repr(e))
        return str(e)

# ---------------- VERIFY OTP ----------------
@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    email = request.form["email"]
    otp = request.form["otp"]

    if email in otp_storage and otp_storage[email]["otp"] == otp:
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
        return render_template("output.html", schemes=[], message="Age limit exceeded")

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM schemes")
    schemes = cur.fetchall()

    result = []

    for s in schemes:
        try:
            if (
                s["caste"].lower() in [caste, "all"] and
                s["gender"].lower() in [gender, "all"] and
                income <= int(s["income"])
            ):
                result.append(dict(s))
        except:
            pass

    return render_template("output.html", schemes=result)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
