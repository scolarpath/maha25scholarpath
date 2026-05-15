from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
import random
import re
import sqlite3
import logging
import threading
from datetime import datetime

# ---------------- APP ----------------

app = Flask(__name__)
app.secret_key = "Maha25ScholarPathSecureKey"

# ---------------- SQLITE ----------------

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

# ---------------- MAIL ----------------

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'maha25scholarpath.noreply@gmail.com'
app.config['MAIL_PASSWORD'] = 'nzee dymu qfmw domm'
app.config['MAIL_DEFAULT_SENDER'] = 'maha25scholarpath.noreply@gmail.com'

mail = Mail(app)

# ---------------- OTP STORAGE ----------------

otp_storage = {}

# ---------------- VALIDATION ----------------

def valid_email(email):
    return re.match(r'^[\w.-]+@[\w.-]+\.\w+$', email)

# ---------------- HOME ----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/home")
def home():
    return render_template("home.html")

# ---------------- 🔥 ASYNC EMAIL SENDER (FIX) ----------------

def send_email_async(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
            print("OTP sent successfully")
        except Exception as e:
            print("Mail error:", e)

# ---------------- OTP SEND (FIXED) ----------------

@app.route("/send_otp", methods=["POST"])
def send_otp():
    email = request.form.get("email")

    if not valid_email(email):
        return "Invalid email format"

    otp = str(random.randint(100000, 999999))
    otp_storage[email] = otp

    msg = Message(
        subject="Maha25 ScholarPath OTP Verification",
        recipients=[email],
        body=f"Your OTP is: {otp}"
    )

    # 🔥 NON-BLOCKING SEND (IMPORTANT FIX)
    threading.Thread(
        target=send_email_async,
        args=(app, msg)
    ).start()

    return render_template("verify.html", email=email)

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

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (name, email, password) VALUES (?,?,?)",
        (name, email, password)
    )
    conn.commit()
    conn.close()

    return redirect("/home")

# ---------------- LOGIN ----------------

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"].strip()
    password = request.form["password"].strip()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, password)
    )

    user = cursor.fetchone()
    conn.close()

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

# ---------------- SEARCH (SQLITE SAFE) ----------------

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

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM schemes")
    rows = cursor.fetchall()
    conn.close()

    eligible = []
    user_level = education_levels.get(education, 0)

    for r in rows:
        try:
            scheme_caste = str(r["caste"]).lower()
            scheme_gender = str(r["gender"]).lower()
            scheme_income = int(r["income"])
            scheme_level = education_levels.get(str(r["education"]), 0)

            if (
                (scheme_caste in [caste, "all"]) and
                (scheme_gender in [gender, "all", "any"]) and
                income <= scheme_income and
                user_level >= scheme_level
            ):
                eligible.append(dict(r))

        except:
            pass

    return render_template("output.html", schemes=eligible)

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
