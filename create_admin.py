import sqlite3
import getpass
from werkzeug.security import generate_password_hash
import os

DB_FILE = "database.db"

def create_admin():
    print("--- Create New Admin User ---")
    username = input("Enter username: ").strip()
    if not username:
        print("Error: Username cannot be empty.")
        return

    password = getpass.getpass("Enter password: ")
    confirm_password = getpass.getpass("Confirm password: ")

    if password != confirm_password:
        print("Error: Passwords do not match.")
        return

    register_number = input("Enter register number (e.g., ADMIN01): ").strip().upper()
    department = "ADMIN"

    hashed_pw = generate_password_hash(password)

    if not os.path.exists(DB_FILE):
        print(f"Error: {DB_FILE} not found. Please run app.py first to initialize the database.")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT * FROM users WHERE username = ? OR register_number = ?", (username, register_number))
        if cursor.fetchone():
            print("Error: A user with this username or register number already exists.")
            conn.close()
            return

        cursor.execute(
            "INSERT INTO users (username, password, register_number, department, is_admin) VALUES (?, ?, ?, ?, ?)",
            (username, hashed_pw, register_number, department, 1)
        )
        conn.commit()
        conn.close()
        print(f"Successfully created admin user: {username}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    create_admin()
