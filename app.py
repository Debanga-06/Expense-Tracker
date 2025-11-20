from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecret")

# Auto-detect database (SQLite for local, PostgreSQL for Render)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL or "sqlite:///expense.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
CORS(app)


# ==================== DATABASE MODELS ====================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    date = db.Column(db.Date, nullable=False)


with app.app_context():
    db.create_all()


# ==================== ROUTES ====================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data["username"]
    email = data["email"]
    password = data["password"]

    existing = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()

    if existing:
        return jsonify({"error": "Username or email already exists"}), 400

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")

    new_user = User(username=username, email=email, password=hashed)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Registration successful"})


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data["username"]
    password = data["password"]

    user = User.query.filter_by(username=username).first()

    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error": "Invalid username or password"}), 400

    session["user_id"] = user.id
    session["username"] = user.username

    return jsonify({"message": "Login successful", "username": user.username})


@app.route("/check_session")
def check_session():
    if "user_id" in session:
        return jsonify({"logged_in": True, "username": session["username"]})
    return jsonify({"logged_in": False})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


# ====================== EXPENSE ROUTES ======================

@app.route("/expenses", methods=["POST"])
def add_expense():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    new_exp = Expense(
        user_id=session["user_id"],
        amount=float(data["amount"]),
        category=data["category"],
        description=data.get("description", ""),
        date=datetime.strptime(data["date"], "%Y-%m-%d")
    )

    db.session.add(new_exp)
    db.session.commit()
    return jsonify({"message": "Expense added"})


@app.route("/expenses", methods=["GET"])
def list_expenses():
    if "user_id" not in session:
        return jsonify([])

    expenses = Expense.query.filter_by(user_id=session["user_id"]) \
        .order_by(Expense.date.desc()).all()

    return jsonify([
        {
            "id": e.id,
            "amount": e.amount,
            "category": e.category,
            "description": e.description,
            "date": e.date.strftime("%Y-%m-%d")
        } for e in expenses
    ])


@app.route("/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    exp = Expense.query.get(expense_id)
    if not exp or exp.user_id != session["user_id"]:
        return jsonify({"error": "Not allowed"}), 403

    db.session.delete(exp)
    db.session.commit()
    return jsonify({"message": "Deleted"})


# ===================== ANALYTICS =====================

@app.route("/analytics")
def analytics():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    expenses = Expense.query.filter_by(user_id=session["user_id"]).all()

    # Category totals
    category_data = {}
    for e in expenses:
        category_data[e.category] = category_data.get(e.category, 0) + e.amount

    category_out = [
        {"category": c, "amount": a} for c, a in category_data.items()
    ]

    # Monthly totals
    monthly = {}
    for e in expenses:
        key = e.date.strftime("%b %Y")
        monthly[key] = monthly.get(key, 0) + e.amount

    monthly_out = [
        {"month": m, "amount": a} for m, a in monthly.items()
    ]

    total = sum(e.amount for e in expenses)

    return jsonify({
        "total_expenses": total,
        "category_data": category_out,
        "monthly_data": monthly_out
    })


# ====================== RUN ======================

if __name__ == "__main__":
    app.run(debug=True)
