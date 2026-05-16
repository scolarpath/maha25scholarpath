from flask import Flask, render_template, request, redirect, session
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
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

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

# ---------------- VALIDATION ----------------
def valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

# ---------------- ROUTES ----------------

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
    return redirect(request.referrer or "/home")

# ---------------- SEND OTP (SENDGRID) ----------------
@app.route("/send_otp", methods=["POST"])
def send_otp():
    email = request.form.get("email")

    if not email:
        return "Email required"

    if not valid_email(email):
        return "Invalid email format"

    otp = str(random.randint(100000, 999999))
    otp_storage[email] = {"otp": otp, "time": time.time()}

    try:
        message = Mail(
            from_email="maha25scholarpath.noreply@gmail.com",  # MUST match SendGrid verified sender
            to_emails=email,
            subject="OTP Verification",
            plain_text_content=f"Your OTP is: {otp}"
        )

        sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
        sg.send(message)

        return "OTP sent successfully"

    except Exception as e:
        print("SENDGRID ERROR:", repr(e))
        return str(e)

# ---------------- VERIFY OTP ----------------
@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    email = request.form.get("email")
    user_otp = request.form.get("otp")

    data = otp_storage.get(email)

    if not data:
        return "OTP not found"

    if time.time() - data["time"] > OTP_EXPIRY_TIME:
        otp_storage.pop(email, None)
        return "OTP expired"

    if data["otp"] == user_otp:
        session["verified_email"] = email
        session["email"] = email
        otp_storage.pop(email, None)
        return redirect("/home")

    return "Invalid OTP"

# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
    user = cur.fetchone()
    conn.close()

    if user:
        session["user"] = email
        session["email"] = email
        return redirect("/information")

    return "Invalid email or password"

# ---------------- REGISTER ----------------
@app.route("/register", methods=["POST"])
def register():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    otp = request.form["otp"]

    if otp_storage.get(email, {}).get("otp") != otp:
        return "Invalid OTP"

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
        (name, email, password)
    )

    conn.commit()
    conn.close()

    otp_storage.pop(email, None)

    return redirect("/home")

# ---------------- SEARCH ----------------
@app.route("/search", methods=["POST"])
def search():
    caste = request.form["caste"].lower()
    gender = request.form["gender"].lower()
    income = int(request.form["income"])
    age = int(request.form["age"])

    if age > 25:
        msg = "Only users aged 25 or below allowed"
        return render_template("output.html", schemes=[], message=msg)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM schemes")
    rows = cur.fetchall()
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
