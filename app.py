from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
import hashlib
import datetime
import json
import os

from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
CORS(app)

# ==========================================================
# PostgreSQL CONFIG (Render uses DATABASE_URL)
# ==========================================================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("❌ DATABASE_URL is not set. Add it in Render environment variables.")

# Required fix for old postgres:// format
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ==========================================================
# DATABASE MODELS
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
# Helper: Hash Password
# ==========================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ==========================================================
# Login Required Decorator
# ==========================================================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated


# ==========================================================
# ROUTES
# ==========================================================

@app.route("/")
def index():
    return render_template("index.html")


# ------------------ REGISTER ------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not all([username, email, password]):
        return jsonify({"error": "All fields are required"}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "Username or email already exists"}), 400

    user = User(
        username=username,
        email=email,
        password=hash_password(password)
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


# ------------------ LOGIN ------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = hash_password(data.get("password"))

    user = User.query.filter_by(username=username, password=password).first()

    if not user:
        return jsonify({"error": "Invalid username or password"}), 401

    session["user_id"] = user.id
    session["username"] = user.username
    return jsonify({"message": "Login successful", "username": user.username}), 200


# ------------------ LOGOUT ------------------
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200


# ------------------ ADD + GET EXPENSES ------------------
@app.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses():
    if request.method == "POST":
        data = request.get_json()

        amount = data.get("amount")
        category = data.get("category")
        description = data.get("description", "")
        date = data.get("date")

        if not all([amount, category, date]):
            return jsonify({"error": "Amount, category, and date are required"}), 400

        expense = Expense(
            user_id=session["user_id"],
            amount=float(amount),
            category=category,
            description=description,
            date=datetime.datetime.strptime(date, "%Y-%m-%d")
        )

        db.session.add(expense)
        db.session.commit()

        return jsonify({"message": "Expense added successfully"}), 201

    # GET expenses
    expenses = Expense.query.filter_by(user_id=session["user_id"]).order_by(Expense.date.desc()).all()
    result = [
        {
            "id": e.id,
            "amount": e.amount,
            "category": e.category,
            "description": e.description,
            "date": e.date.strftime("%Y-%m-%d")
        }
        for e in expenses
    ]

    return jsonify(result)


# ------------------ DELETE EXPENSE ------------------
@app.route("/expenses/<int:expense_id>", methods=["DELETE"])
@login_required
def delete_expense(expense_id):
    exp = Expense.query.filter_by(id=expense_id, user_id=session["user_id"]).first()

    if not exp:
        return jsonify({"error": "Expense not found"}), 404

    db.session.delete(exp)
    db.session.commit()

    return jsonify({"message": "Expense deleted successfully"}), 200


# ------------------ ANALYTICS ------------------
@app.route("/analytics", methods=["GET"])
@login_required
def analytics():
    user_id = session["user_id"]

    # Category summary
    category_rows = db.session.query(
        Expense.category, db.func.sum(Expense.amount)
    ).filter_by(user_id=user_id).group_by(Expense.category).all()

    category_data = [
        {"category": cat, "amount": total}
        for cat, total in category_rows
    ]

    # Monthly summary
    current_year = datetime.datetime.now().year

    monthly_rows = db.session.query(
        db.extract("month", Expense.date), db.func.sum(Expense.amount)
    ).filter(
        Expense.user_id == user_id,
        db.extract("year", Expense.date) == current_year
    ).group_by(
        db.extract("month", Expense.date)
    ).order_by(
        db.extract("month", Expense.date)
    ).all()

    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    monthly_data = [
        {"month": months[int(month)-1], "amount": total}
        for month, total in monthly_rows
    ]

    # Total expenses
    total_expenses = db.session.query(db.func.sum(Expense.amount)).filter_by(user_id=user_id).scalar() or 0

    return jsonify({
        "category_data": category_data,
        "monthly_data": monthly_data,
        "total_expenses": total_expenses
    })


@app.route("/check_session")
def check_session():
    if "user_id" in session:
        return jsonify({"logged_in": True, "username": session["username"]})
    return jsonify({"logged_in": False})


# ==========================================================
# RUN (creates tables automatically)
# ==========================================================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
