from flask import Flask, render_template, request, redirect, session
import random
import re
import sqlite3
import requests
import logging

# ---------------- APP ----------------

app = Flask(__name__)
app.secret_key = "Maha25ScholarPathSecureKey"

# ---------------- FAST2SMS API ----------------
FAST2SMS_API_KEY = "REPLACE_WITH_YOUR_NEW_KEY"

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

otp_storage = {}

# ---------------- VALIDATION ----------------

def valid_email(email):
    return re.match(r'^[\w.-]+@[\w.-]+\.\w+$', email)

def send_sms_otp(number, otp):
    url = "https://www.fast2sms.com/dev/bulkV2"

    payload = {
        "authorization": FAST2SMS_API_KEY,
        "route": "otp",
        "variables_values": otp,
        "numbers": number
    }

    headers = {
        "cache-control": "no-cache"
    }

    response = requests.post(url, data=payload, headers=headers)
    logging.info(f"SMS response: {response.text}")

# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/home")
def home():
    return render_template("home.html")

# ---------------- OTP SEND (FINAL FIX) ----------------

@app.route("/send_otp", methods=["POST"])
def send_otp():
    email = request.form.get("email")
    number = request.form.get("number")

    if not valid_email(email):
        return "Invalid email format"

    if not number:
        return "Phone number required"

    otp = str(random.randint(100000, 999999))
    otp_storage[email] = otp

    try:
        send_sms_otp(number, otp)
        logging.info(f"OTP sent to {number}")
        return render_template("verify.html", email=email)

    except Exception as e:
        logging.error(f"OTP failed: {e}")
        return "Failed to send OTP"

# ---------------- VERIFY OTP ----------------

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    email = request.form.get("email")
    user_otp = request.form.get("otp")

    if otp_storage.get(email) == user_otp:
        session["verified_email"] = email
        return redirect("/home")

    return "Invalid OTP"

# ---------------- SEARCH (SAFE BASIC VERSION) ----------------

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
