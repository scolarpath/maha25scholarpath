from flask import Flask, render_template, request, redirect, session
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

import sqlite3
import pandas as pd
import random
import re
import time
import os
import logging

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)

# ---------------- DB ----------------
def init_db():

    conn = sqlite3.connect("data.db")
    cur = conn.cursor()

    # USERS TABLE
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


def get_db():
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- APP ----------------
app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "dev_secret")

# IMPORTANT FOR RENDER
with app.app_context():
    init_db()


# ---------------- OTP STORAGE ----------------
otp_storage = {}

OTP_EXPIRY = 300


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

    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        return "Missing fields"

    email = email.strip().lower()

    db = get_db()

    cur = db.cursor()

    cur.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, password)
    )

    user = cur.fetchone()

    db.close()

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
    otp = otp.strip()

    data = otp_storage.get(email)

    if not data:
        return "Please request OTP first"

    # OTP expiry
    if time.time() - data["time"] > OTP_EXPIRY:
        otp_storage.pop(email, None)
        return "OTP expired"

    # OTP verify
    if data["otp"] != otp:
        return "Invalid OTP"

    try:

        db = get_db()

        cur = db.cursor()

        cur.execute(
            "INSERT INTO users(name,email,password) VALUES (?,?,?)",
            (name, email, password)
        )

        db.commit()

        db.close()

        otp_storage.pop(email, None)

        return redirect("/home")

    except sqlite3.IntegrityError:
        return "Email already registered"

    except Exception as e:
        print("REGISTER ERROR:", e)
        return "Registration failed"


# ---------------- SEND OTP ----------------
@app.route("/send_otp", methods=["POST"])
def send_otp():

    email = request.form.get("email")

    if not email:
        return "Email required"

    email = email.strip().lower()

    if not valid_email(email):
        return "Invalid email"

    otp = str(random.randint(100000, 999999))

    otp_storage[email] = {
        "otp": otp,
        "time": time.time()
    }

    try:

        message = Mail(
            from_email="maha25scholarpath.noreply@gmail.com",
            to_emails=email,
            subject="OTP Verification - Maha25 ScholarPath",
            plain_text_content=f"Your OTP is: {otp}"
        )

        sg = SendGridAPIClient(
            os.environ.get("SENDGRID_API_KEY")
        )

        response = sg.send(message)

        print("SENDGRID STATUS:", response.status_code)

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

    # expiry check
    if time.time() - data["time"] > OTP_EXPIRY:
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

    try:

        df = pd.read_csv("dataset.csv")

    except Exception as e:

        print("CSV ERROR:", e)

        return "dataset.csv not found"

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

                scheme_data = {
                    "name": row["name_of_scheme"],
                    "gender": row["gender"],
                    "caste": row["caste"],
                    "income": row["annual_income"],
                    "education": row["educational_qualification"],
                    "link": row["link"],
                    "documents": row["required_documents"]
                }

                days_left = 10
                status = "Open"

                eligible.append((scheme_data, days_left, status))

        except Exception as e:
            print("ROW ERROR:", e)

    return render_template(
        "output.html",
        schemes=eligible
    )
# ---------------- RUN ----------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(host="0.0.0.0", port=port)
