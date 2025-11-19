from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import sqlite3
import hashlib
import datetime
import json
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
CORS(app)

# Database initialization
def init_db():
    conn = sqlite3.connect('expense_tracker.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Expenses table
    c.execute('''CREATE TABLE IF NOT EXISTS expenses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  amount REAL NOT NULL,
                  category TEXT NOT NULL,
                  description TEXT,
                  date DATE NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    conn.commit()
    conn.close()

# Helper function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not all([username, email, password]):
        return jsonify({'error': 'All fields are required'}), 400
    
    conn = sqlite3.connect('expense_tracker.db')
    c = conn.cursor()
    
    try:
        hashed_password = hash_password(password)
        c.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                  (username, email, hashed_password))
        conn.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username or email already exists'}), 400
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not all([username, password]):
        return jsonify({'error': 'Username and password are required'}), 400
    
    conn = sqlite3.connect('expense_tracker.db')
    c = conn.cursor()
    
    hashed_password = hash_password(password)
    c.execute('SELECT id, username FROM users WHERE username = ? AND password = ?',
              (username, hashed_password))
    user = c.fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user[0]
        session['username'] = user[1]
        return jsonify({'message': 'Login successful', 'username': user[1]}), 200
    else:
        return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/expenses', methods=['GET', 'POST'])
@login_required
def expenses():
    conn = sqlite3.connect('expense_tracker.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.get_json()
        amount = data.get('amount')
        category = data.get('category')
        description = data.get('description', '')
        date = data.get('date')
        
        if not all([amount, category, date]):
            return jsonify({'error': 'Amount, category, and date are required'}), 400
        
        try:
            c.execute('INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)',
                      (session['user_id'], float(amount), category, description, date))
            conn.commit()
            return jsonify({'message': 'Expense added successfully'}), 201
        except ValueError:
            return jsonify({'error': 'Invalid amount'}), 400
        finally:
            conn.close()
    
    else:  # GET request
        c.execute('SELECT id, amount, category, description, date FROM expenses WHERE user_id = ? ORDER BY date DESC',
                  (session['user_id'],))
        expenses = []
        for row in c.fetchall():
            expenses.append({
                'id': row[0],
                'amount': row[1],
                'category': row[2],
                'description': row[3],
                'date': row[4]
            })
        conn.close()
        return jsonify(expenses)

@app.route('/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):
    conn = sqlite3.connect('expense_tracker.db')
    c = conn.cursor()
    
    c.execute('DELETE FROM expenses WHERE id = ? AND user_id = ?', (expense_id, session['user_id']))
    if c.rowcount > 0:
        conn.commit()
        conn.close()
        return jsonify({'message': 'Expense deleted successfully'}), 200
    else:
        conn.close()
        return jsonify({'error': 'Expense not found'}), 404

@app.route('/analytics', methods=['GET'])
@login_required
def analytics():
    conn = sqlite3.connect('expense_tracker.db')
    c = conn.cursor()
    
    # Category-wise expenses
    c.execute('''SELECT category, SUM(amount) 
                 FROM expenses 
                 WHERE user_id = ? 
                 GROUP BY category''', (session['user_id'],))
    
    category_data = []
    for row in c.fetchall():
        category_data.append({'category': row[0], 'amount': row[1]})
    
    # Monthly expenses for the current year
    current_year = datetime.datetime.now().year
    c.execute('''SELECT strftime('%m', date) as month, SUM(amount) 
                 FROM expenses 
                 WHERE user_id = ? AND strftime('%Y', date) = ? 
                 GROUP BY strftime('%m', date)
                 ORDER BY month''', (session['user_id'], str(current_year)))
    
    monthly_data = []
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for row in c.fetchall():
        month_num = int(row[0]) - 1
        monthly_data.append({'month': months[month_num], 'amount': row[1]})
    
    # Total expenses
    c.execute('SELECT SUM(amount) FROM expenses WHERE user_id = ?', (session['user_id'],))
    total = c.fetchone()[0] or 0
    
    conn.close()
    
    return jsonify({
        'category_data': category_data,
        'monthly_data': monthly_data,
        'total_expenses': total
    })

@app.route('/check_session')
def check_session():
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'username': session['username']})
    else:
        return jsonify({'logged_in': False})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)