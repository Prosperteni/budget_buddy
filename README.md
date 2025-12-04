# BudgetBuddy



**BudgetBuddy** is a personal finance management application designed to help users track their expenses, analyze their spending patterns, and manage their budget efficiently. Built with Flask, Bootstrap, and Python, BudgetBuddy aims to provide an intuitive interface and a variety of features to make personal finance management easier and more accessible.

## Features

* **User Authentication**: Secure login and registration system to protect user data.
* **Profile Management**: Users can update personal information, change their profile picture, and update their password.
* **Transactions Management**: Users can add, view, and categorize their financial transactions.
* **Analytics and Reporting**: Users can view detailed analytics on their spending, track trends, and generate PDF reports of their transactions.
* **Responsive UI**: Built with Bootstrap, ensuring a seamless experience across devices, including desktop and mobile.
* **Database Integration**: Uses SQLite for persistent storage of user data and transactions.

## Tech Stack

* **Backend**: Flask (Python)
* **Frontend**: HTML, CSS (Bootstrap)
* **Database**: SQLite
* **Authentication**: Flask-Login for user management
* **Version Control**: Git, GitHub

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

* Python (version 3.x)
* pip (Python package installer)

### Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/Prosperteni/budget-buddy.git
   ```

2. **Navigate to the project directory**:

   ```bash
   cd budget-buddy
   ```

3. **Create a virtual environment** (recommended):

   ```bash
   python3 -m venv venv
   ```

4. **Activate the virtual environment**:

   * On Windows:

     ```bash
     venv\Scripts\activate
     ```
   * On macOS/Linux:

     ```bash
     source venv/bin/activate
     ```

5. **Install the required dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

6. **Set up the database**:

   * Run the following command to initialize the SQLite database:

     ```bash
     flask db upgrade
     ```

7. **Run the application**:

   ```bash
   flask run
   ```

   * Visit `http://127.0.0.1:5000` in your web browser to access the application.

## Usage

* **Register a new account** or **log in** to an existing one.
* **Manage your profile**, including updating your username, email, and bio.
* **Track your expenses** by adding transactions, categorize them, and view your financial reports.
* **Download PDF reports** of your transactions for offline tracking.
* **Change your password** and manage your account settings.

## File Structure

```bash
├── app.py                # Main Flask application
├── requirements.txt      # Project dependencies
├── templates/            # HTML templates
│   ├── base.html
│   ├── profile.html
│   ├── dashboard.html
│   └── ... 
├── static/               # CSS, JavaScript, and image files
├── venv/                 # Virtual environment
└── .gitignore            # Git ignore file for sensitive data (e.g., .env)
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

* **Flask** for making it easy to build web applications with Python.
* **Bootstrap** for providing responsive, mobile-first UI components.
* **SQLite** for a simple, file-based database.

---

### Regarding `.gitignore` for the `.env` file:

Make sure that your `.env` file (where your secret keys and environment variables are stored) is added to the `.gitignore` file. Here's the updated `.gitignore` section:

```bash
# Ignore .env file for storing sensitive data like API keys
.env
```

This will prevent your `.env` file from being tracked by Git and pushed to GitHub, keeping your API keys and sensitive credentials secure.
