from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
import random
import re
import sqlite3
import logging
from datetime import datetime

# ---------------- APP ----------------

app = Flask(__name__)
app.secret_key = "Maha25ScholarPathSecureKey"

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

# ---------------- OTP SEND (FIXED - NO FAKE SUCCESS) ----------------

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

    try:
        mail.send(msg)
        logging.info(f"OTP sent to {email}")
        return render_template("verify.html", email=email)

    except Exception as e:
        logging.error(f"OTP FAILED for {email}: {e}")
        return "Failed to send OTP. Try again."

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
    email = request.form["email"]
    password = request.form["password"]

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

# ---------------- SEARCH (SAFE SQLITE) ----------------

education_levels = {
    "10th": 1,
    "12th": 2,
    "Graduate": 3,
    "Post-Graduate": 4
}

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
            if (
                str(r["caste"]).lower() in [caste, "all"] and
                str(r["gender"]).lower() in [gender, "all", "any"] and
                income <= int(r["income"]) and
                user_level >= education_levels.get(r["education"], 0)
            ):
                eligible.append(dict(r))
        except:
            pass

    return render_template("output.html", schemes=eligible)

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
