from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
import sqlite3
import random
import re
import time
import logging
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# ---------------- APP ----------------
app = Flask(__name__)

# REQUIRED for sessions
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# ---------------- MAIL CONFIG ----------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("EMAIL_USER")
app.config['MAIL_PASSWORD'] = os.environ.get("EMAIL_PASS")
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)   # ✅ FIXED (IMPORTANT)

# ---------------- LOGGING ----------------
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

# ---------------- DB ----------------
def get_db():
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- OTP STORAGE ----------------
otp_storage = {}
OTP_EXPIRY_TIME = 300

# ---------------- EMAIL VALIDATION ----------------
def valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/home")
def home():
    return render_template("home.html")

# ---------------- SEND OTP ----------------
@app.route("/send_otp", methods=["POST"])
def send_otp():
    email = request.form.get("email")

    if not email:
        return "Email required"

    otp = str(random.randint(100000, 999999))
    otp_storage[email] = {"otp": otp, "time": time.time()}

    try:
        message = Mail(
            from_email="your_verified_sendgrid_email@example.com",
            to_emails=email,
            subject="OTP Verification",
            plain_text_content=f"Your OTP is: {otp}"
        )

        sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
        sg.send(message)

        print("OTP SENT VIA SENDGRID")

        return "OTP sent successfully"

    except Exception as e:
     print("SENDGRID FULL ERROR:", repr(e))
     return str(e)

# ---------------- VERIFY OTP ----------------
@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    email = request.form.get("email")
    user_otp = request.form.get("otp")

    data = otp_storage.get(email)

    if not data:
        return "OTP expired or not found"

    if time.time() - data["time"] > OTP_EXPIRY_TIME:
        otp_storage.pop(email, None)
        return "OTP expired"

    if data["otp"] == user_otp:
        session["verified_email"] = email
        otp_storage.pop(email, None)
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

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schemes")
    rows = cursor.fetchall()
    conn.close()

    eligible = []

    for r in rows:
        try:
            if (
                str(r["caste"]).lower() in [caste, "all"] and
                str(r["gender"]).lower() in [gender, "all", "any"] and
                income <= int(r["income"])
            ):
                eligible.append(dict(r))
        except:
            pass

    return render_template("output.html", schemes=eligible)

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
