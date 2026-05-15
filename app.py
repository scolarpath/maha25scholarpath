from flask import Flask, render_template, request, redirect, session
import random
import re
import sqlite3
import requests
import logging
import smtplib
import time
from email.mime.text import MIMEText

# ---------------- APP ----------------

app = Flask(__name__)
app.secret_key = "Maha25ScholarPathSecureKey"

# ---------------- CONFIG ----------------

FAST2SMS_API_KEY = "Xk2LJY05znqufLKP90C8j995dqaSlJjpIhwxigc0hFpDIWD62JzWUhNrAEaf"

EMAIL_SENDER = "maha25scholarpath.noreply@gmail.com"
EMAIL_PASSWORD = "dkne cbte vsbz tnai"   # Gmail App Password ONLY

OTP_EXPIRY_TIME = 300  # 5 minutes

# ---------------- DB ----------------

def get_db():
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- LOGGING ----------------

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

# ---------------- OTP STORAGE ----------------
# format: { email: {"otp": "123456", "time": timestamp, "number": phone} }

otp_storage = {}

# ---------------- VALIDATION ----------------

def valid_email(email):
    return re.match(r'^[\w.-]+@[\w.-]+\.\w+$', email)

# ---------------- SMS OTP ----------------

def send_sms_otp(number, otp):
    url = "https://www.fast2sms.com/dev/bulkV2"

    payload = {
        "authorization": FAST2SMS_API_KEY,
        "route": "otp",
        "variables_values": otp,
        "numbers": number
    }

    response = requests.post(url, data=payload)

    logging.info(f"SMS response: {response.text}")

    if response.status_code != 200:
        raise Exception("SMS sending failed")

# ---------------- EMAIL OTP ----------------

def send_email_otp(email, otp):
    try:
        print("EMAIL FUNCTION STARTED")

        msg = MIMEText(f"Your OTP for verification is: {otp}")
        msg["Subject"] = "OTP Verification"
        msg["From"] = EMAIL_SENDER
        msg["To"] = email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.set_debuglevel(1)  # shows real connection logs
        server.starttls()

        print("Logging into Gmail...")
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)

        print("Sending email...")
        server.sendmail(EMAIL_SENDER, email, msg.as_string())

        server.quit()

        print("EMAIL SENT SUCCESSFULLY")
        logging.info(f"Email OTP sent to {email}")

    except Exception as e:
        print("EMAIL ERROR:", e)
        logging.error(f"Email failed: {e}")

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
    number = request.form.get("number")

    if not valid_email(email):
        return "Invalid email format"

    if not number:
        return "Phone number required"

    otp = str(random.randint(100000, 999999))

    otp_storage[email] = {
        "otp": otp,
        "time": time.time(),
        "number": number
    }

    try:
        send_sms_otp(number, otp)
        send_email_otp(email, otp)

        logging.info(f"OTP sent to {email}, {number}")

        return render_template("verify.html", email=email)

    except Exception as e:
        logging.error(f"OTP failed: {e}")
        return "Failed to send OTP"

# ---------------- VERIFY OTP ----------------

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    email = request.form.get("email")
    user_otp = request.form.get("otp")

    data = otp_storage.get(email)

    if not data:
        return "OTP not found or expired"

    # check expiry
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
    education = request.form["education"]
    age = int(request.form["age"])

    if age > 25:
        return render_template("output.html", schemes=[], message="Only users aged 25 or below allowed")

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
    app.run(host="0.0.0.0", port=5000)
