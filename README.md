# 💰 Expense Tracker

A simple and efficient **Expense Tracker Web App** built with **Python**, **Flask**, and **SQLite**.  
This app helps users track their daily expenses, categorize spending, and view summaries in a clean UI.

---

## 🚀 Features

- ➕ Add new expenses with description, amount, and category  
- 📂 View all expenses in a table  
- 🗂 Categorize expenses (Food, Travel, Shopping, etc.)  
- 🔍 Filter expenses by category  
- 🗑 Delete expenses  
- 💾 Data stored locally using SQLite (`expense.db`)  
- 🌐 Ready for deployment on **Render**

---

## 🛠 Tech Stack

- **Backend:** Python, Flask  
- **Database:** SQLite  
- **Frontend:** HTML, CSS, Bootstrap  
- **Deployment:** Render (Gunicorn)

---

## 📦 Installation

Clone the repository:

```sh
git clone https://github.com/your-username/expense-tracker.git
cd expense-tracker
```
Create and activate a virtual environment:
```sh
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```
Install dependencies:
```
pip install -r requirements.txt
```
▶️ Run the App Locally
```
python app.py
```
The app will run at:

    http://127.0.0.1:5000/

🚀 Deploying on Render

Make sure your ``requirements.txt`` includes:
```
flask
gunicorn
```
Render Build Command
```pip install -r requirements.txt```
Render Start Command
```gunicorn app:app```
📁 Project Structure
```
expense-tracker/
│
├── app.py
├── expense.db         # (Ignored using .gitignore)
├── requirements.txt
├── static/
│   └── styles.css
└── templates/
    ├── index.html
```
📝 .gitignore (Recommended)
```
venv/
__pycache__/
*.db
*.sqlite3
```

🚀 Live Demo 
      [https://expense-tracker-kx06.onrender.com]
      
📜 License

    This project is open-source and available under the MIT License.
   
🙌 Contributing

      Pull requests are welcome!
      Feel free to open an issue if you want to suggest improvements or new features.
   
❤️ Support

     If you like this project, consider giving it a ⭐ on GitHub!
