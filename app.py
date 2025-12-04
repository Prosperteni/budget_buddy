from flask import Flask, flash, redirect, render_template, request, url_for, Blueprint, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from helpers import build_transaction_pdf, get_transaction_data, get_transaction_summary, format_transactions, get_last_month_expenses
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta
import requests
import os
from dotenv import load_dotenv


GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# -------------------- Setup Flask App --------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# Blueprint for reports
report_bp = Blueprint("report", __name__)


# -------------------- Flask-Login Setup --------------------
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

# -------------------- User Class --------------------


class User(UserMixin):
    def __init__(self, id_, username):
        self.id = id_
        self.username = username

    @staticmethod
    def get(user_id):
        conn = sqlite3.connect("finance.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cur.fetchone()
        conn.close()
        if not user:
            return None
        return User(user["id"], user["username"])


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# -------------------- DB Connection Helper --------------------


def get_db_connection():
    conn = sqlite3.connect("finance.db")
    conn.row_factory = sqlite3.Row
    return conn

# -------------------- Database Setup Function --------------------
def init_db():
    try:
        # Use the same database name 'finance.db'
        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                hash TEXT NOT NULL
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

        conn.commit()
        print("Database setup complete: users and transactions tables ensured.")
    except Exception as e:
        print(f"Error during database initialization: {e}")
    finally:
        if conn:
            conn.close()

# -------------------- Routes --------------------


@app.route("/", methods=["GET", "POST"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

# -------- Login Route --------


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password")

        if not username or not password:
            flash("Must provide username and password", "danger")
            return render_template("login.html")

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE username = ?", (username,))
            user_data = cur.fetchone()

        if user_data is None or not check_password_hash(user_data["hash"], password):
            flash("Invalid username or password", "danger")
            return render_template("login.html")

        user_obj = User(user_data["id"], user_data["username"])
        login_user(user_obj)

        flash("Login successful!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


# -------- Register Route --------
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Basic validation
        if not username:
            flash("Must provide username", "danger")
            return render_template("register.html")
        if not password:
            flash("Must provide password", "danger")
            return render_template("register.html")
        if password != confirmation:
            flash("Passwords do not match", "danger")
            return render_template("register.html")

        # Password complexity check (optional but recommended)
        if len(password) < 8:
            flash("Password must be at least 8 characters long", "danger")
            return render_template("register.html")

        # Check if the username already exists
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE username = ?", (username,))
            if cur.fetchone():
                flash("Username already exists", "warning")
                return render_template("register.html")

            # Hash the password and store in the database
            hashed_pw = generate_password_hash(password)
            cur.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (username, hashed_pw))
            conn.commit()

        flash("Registered successfully! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# -------- Logout Route --------


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# -------- Dashboard --------
@app.route("/dashboard")
@login_required
def dashboard():
    user_id = current_user.id
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='income'", (user_id,))
        total_income = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='expenses'", (user_id,))
        total_expenses = cur.fetchone()[0] or 0

        balance = total_income - total_expenses

        cur.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC LIMIT 5", (user_id,))
        transactions = cur.fetchall()

    transactions = format_transactions(transactions)

    return render_template(
        "dashboard.html",
        total_income=total_income,
        total_expenses=total_expenses,
        balance=balance,
        transactions=transactions,
        user=current_user
    )


@app.route("/dashboard/data")
@login_required
def dashboard_data():
    user_id = current_user.id
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT amount, type, date FROM transactions WHERE user_id=? ORDER BY date ASC", (user_id,))
        rows = cur.fetchall()

        # Total income & expenses for doughnut (Income vs Expenses)
        cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='income'", (user_id,))
        total_income = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='expenses'", (user_id,))
        total_expenses = cur.fetchone()[0] or 0

        # Category breakdown for pie chart (Percent of income spent on each category)
        cur.execute("""
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE user_id=? AND type='expenses'
            GROUP BY category
        """, (user_id,))
        categories_data = cur.fetchall()

    # Calculate percentage of income spent on each category
    category_percentages = {}
    if total_income > 0:
        for row in categories_data:
            category = row[0]
            total_spent = row[1]
            percentage = (total_spent / total_income) * 100  # Calculate percentage
            category_percentages[category] = percentage

    # Prepare data for pie chart
    categories = list(category_percentages.keys())
    percentages = list(category_percentages.values())

    # Prepare trend data
    trends = defaultdict(lambda: {"income": 0, "expenses": 0})
    for row in rows:
        date_str = row["date"]  # Assuming stored as 'YYYY-MM-DD'
        amount = row["amount"]
        txn_type = row["type"]
        if txn_type == "income":
            trends[date_str]["income"] += amount
        else:
            trends[date_str]["expenses"] += amount

    # Sort by date
    sorted_dates = sorted(trends.keys())
    income_trend = [trends[date]["income"] for date in sorted_dates]
    expenses_trend = [trends[date]["expenses"] for date in sorted_dates]

    return jsonify({
        "total_income": total_income,
        "total_expenses": total_expenses,
        "categories": categories,
        "percentages": percentages,
        "dates": sorted_dates,
        "income": income_trend,
        "expenses": expenses_trend
    })


# -------- Transactions --------
@app.route("/transactions", methods=["GET", "POST"])
@login_required
def transactions():
    user_id = current_user.id

    if request.method == "POST":
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO transactions (user_id, description, category, type, amount, date) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    request.form.get("description"),
                    request.form.get("category"),
                    request.form.get("type"),
                    request.form.get("amount"),
                    request.form.get("date")
                )
            )
            conn.commit()
        flash("Transaction added successfully!", "success")
        return redirect(url_for("transactions"))

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC", (user_id,))
        transactions = cur.fetchall()

    transactions = format_transactions(transactions)

    return render_template("transactions.html", transactions=transactions, user=current_user)


@app.route('/delete_transaction/<int:txn_id>', methods=['POST'])
@login_required
def delete_transaction(txn_id):
    try:
        conn = sqlite3.connect('finance.db')
        cursor = conn.cursor()

        # Optional: ensure user can only delete their own transaction
        cursor.execute("SELECT user_id FROM transactions WHERE id=?", (txn_id,))
        row = cursor.fetchone()
        if not row:
            flash("Transaction not found.", "danger")
            return redirect(url_for('transactions'))
        if row[0] != current_user.id:
            flash("Unauthorized action.", "danger")
            return redirect(url_for('transactions'))

        cursor.execute("DELETE FROM transactions WHERE id=?", (txn_id,))
        conn.commit()
        flash("Transaction deleted successfully.", "success")
    except Exception as e:
        flash("Error deleting transaction.", "danger")
    finally:
        conn.close()

    return redirect(url_for('transactions'))

# -------- Analytics --------


@app.route('/analytics', methods=["GET", "POST"])
@login_required
def analytics():
    user_id = current_user.id
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='income'", (user_id,))
        total_income = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='expenses'", (user_id,))
        total_expenses = cur.fetchone()[0] or 0

        cur.execute(
            "SELECT ROUND(AVG(amount), 2) FROM transactions WHERE user_id=? AND type='expenses'", (user_id,))
        avg_expense = cur.fetchone()[0] or 0

        cur.execute("""
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE user_id=? AND type='expenses'
            GROUP BY category
        """, (user_id,))
        categories_data = cur.fetchall()

        category_expenses = {row['category']: row['total'] for row in categories_data}

    balance = total_income - total_expenses

    return render_template("analytics.html",
                           total_income=total_income,
                           total_expenses=total_expenses,
                           balance=balance,
                           category_expenses=category_expenses,
                           avg_expense=avg_expense,
                           user=current_user)


# Route to generate financial summary
@app.route("/analytics/generate_summary", methods=["POST"])
def generate_summary():
    user_data = request.get_json()

    total_expenses = user_data.get("total_expenses", 0)
    total_income = user_data.get("total_income", 0)
    category_expenses = user_data.get("category_expenses", {})

   # Fetch previous month's total expenses (add query to get previous month's data)
    last_month_expenses = get_last_month_expenses(current_user.id)

    # Build a prompt for the AI
    prompt = f"""
    Generate a human-readable financial summary.
    Current Month Income: ${total_income}
    Current Month Expenses: ${total_expenses}
    Previous Month Expenses: ${last_month_expenses}
    Expenses by category: {category_expenses}
    Provide insights, trends, and friendly advice on how to reduce expenses.
    """

    # Send request to Gemini API
    try:
        # Endpoint URL for Gemini API
       # Corrected URL for the OpenAI compatibility layer
        url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

        headers = {
            "Content-Type": "application/json",
            # Note: Using the Bearer token with the Gemini API Key is supported by this compatibility endpoint
            "Authorization": f"Bearer {GEMINI_API_KEY}"
        }
        # Prepare the payload for Gemini API
        data = {
            "model": "gemini-2.5-flash",  # Specify the Gemini model (adjust as per your use case)
            "messages": [
                {"role": "system", "content": "In 5 lines max You are a financial assistant that tells users what they should do to reduce their expences."},
                {"role": "user", "content": prompt}
            ]
        }

        # Make the request to Gemini API
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise error for bad responses

        # Parse the response
        response_json = response.json()
        summary_text = response_json['choices'][0]['message']['content']

        return jsonify({"summary": summary_text})

    except requests.exceptions.RequestException as e:
        # Handle API errors or issues with the request
        return jsonify({"error": str(e)}), 500


# -------- Profile --------
@app.route('/profile', methods=["GET", "POST"])
@login_required
def profile():
    user_id = current_user.id
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
        user = cur.fetchone()

    return render_template("profile.html", user=user)


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        # Get the form data
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')
        submitted_username = request.form.get('username')

        # Validate form fields
        if not old_password or not new_password or not confirm_new_password:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for('profile'))  # Or the profile page

        if new_password != confirm_new_password:
            flash("New passwords do not match.", "danger")
            return redirect(url_for('profile'))  # Or the profile page

        # Ensure the username matches the logged-in user's username
        if submitted_username != current_user.username:
            flash("You cannot change another user's password.", "danger")
            return redirect(url_for('profile'))  # Or the profile page

        # Check if the old password is correct
        conn = sqlite3.connect('finance.db')
        cursor = conn.cursor()
        cursor.execute("SELECT hash FROM users WHERE id = ?", (current_user.id,))
        user = cursor.fetchone()
        conn.close()

        # If the old password is incorrect
        if not check_password_hash(user[0], old_password):  # user[0] is the hash field
            flash("Incorrect old password.", "danger")
            return redirect(url_for('profile'))  # Or the profile page

        # Update the password
        hashed_new_password = generate_password_hash(new_password)

        conn = sqlite3.connect('finance.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET hash = ? WHERE id = ?",
                       (hashed_new_password, current_user.id))
        conn.commit()
        conn.close()

        flash("Password updated successfully!", "success")
        return redirect(url_for('profile'))  # Or the profile page

    return redirect(url_for('profile'))  # In case it's a GET request or something went wrong


@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    # Confirm with the user before deleting
    try:
        conn = sqlite3.connect('finance.db')
        cursor = conn.cursor()

        # Delete all user data from transactions (optional: add more related tables)
        cursor.execute("DELETE FROM transactions WHERE user_id = ?", (current_user.id,))

        # Delete the user's record
        cursor.execute("DELETE FROM users WHERE id = ?", (current_user.id,))
        conn.commit()

        # Log out the user
        logout_user()

        # Close the connection
        conn.close()

        flash("Your account has been deleted successfully.", "success")
        return redirect(url_for('index'))  # Redirect to home page after deletion

    except Exception as e:
        flash("There was an error deleting your account. Please try again later.", "danger")
        return redirect(url_for('profile'))  # Stay on the profile page in case of an error


# -------- Download Report --------
@report_bp.route("/download_report")
@login_required
def download_report():
    user_id = current_user.id

    transactions = get_transaction_data(user_id)
    transactions = format_transactions(transactions)
    total_income, total_expenses, balance = get_transaction_summary(user_id)

    # PDF
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_pdf.close()
    build_transaction_pdf(
        transactions,
        temp_pdf.name,
        total_income,
        total_expenses,
        balance,
    )

    return send_file(
        temp_pdf.name,
        as_attachment=True,
        download_name=f"{current_user.username}_financial_report.pdf"
    )


# Register Blueprint
app.register_blueprint(report_bp)


# -------------------- Server Start --------------------
if __name__ == "__main__":
    # 1. Initialize the database tables
    init_db()  
    
    # 2. Configure port for local development or deployment
    import os # Import os if it's not already imported at the top
    port = int(os.environ.get('PORT', 8080))

    # 3. Start the server (Waitress)
    from waitress import serve
    serve(app, host="0.0.0.0", port=port)