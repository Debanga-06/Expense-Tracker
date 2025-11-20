import os
import datetime
from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default-secret-key")

# ==========================================================
# DATABASE CONFIG
# ==========================================================
if os.getenv("RENDER"):
    # Running on Render → use PostgreSQL
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
else:
    # Local development → use SQLite
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///expense.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ==========================================================
# MODELS
# ==========================================================
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


# ==========================================================
# AUTO CREATE TABLES
# ==========================================================
with app.app_context():
    db.create_all()

# ==========================================================
# ROUTES
# ==========================================================

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect("/login")

    expenses = Expense.query.filter_by(user_id=session["user_id"]).all()
    return render_template("index.html", expenses=expenses)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        existing = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing:
            return "User already exists!"

        hashed_pw = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_pw)
        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            return "Invalid credentials!"

        session["user_id"] = user.id
        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/add_expense", methods=["POST"])
def add_expense():
    if "user_id" not in session:
        return redirect("/login")

    amount = request.form["amount"]
    category = request.form["category"]
    description = request.form.get("description", "")
    date = request.form["date"]

    expense = Expense(
        user_id=session["user_id"],
        amount=float(amount),
        category=category,
        description=description,
        date=datetime.datetime.strptime(date, "%Y-%m-%d").date()
    )

    db.session.add(expense)
    db.session.commit()

    return redirect("/")


@app.route("/delete_expense/<int:id>")
def delete_expense(id):
    expense = Expense.query.get(id)
    if expense and expense.user_id == session["user_id"]:
        db.session.delete(expense)
        db.session.commit()

    return redirect("/")


# ==========================================================
# RUN APP
# ==========================================================
if __name__ == "__main__":
    app.run(debug=True)
