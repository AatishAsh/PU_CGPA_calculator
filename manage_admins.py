import sqlite3
import getpass
from werkzeug.security import generate_password_hash
import os
import sys

DB_FILE = "database.db"

def get_db_connection():
    if not os.path.exists(DB_FILE):
        print(f"Error: {DB_FILE} not found. Please run app.py first to initialize the database.")
        sys.exit(1)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def list_admins():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, register_number, department FROM users WHERE is_admin = 1")
    admins = cursor.fetchall()
    conn.close()

    if not admins:
        print("\nNo admin users found.")
        return

    print("\n--- Admin Users ---")
    print(f"{'Username':<20} | {'Reg Number':<15} | {'Department':<15}")
    print("-" * 55)
    for admin in admins:
        print(f"{admin['username']:<20} | {admin['register_number']:<15} | {admin['department']:<15}")
    print()

def create_admin():
    print("\n--- Create New Admin User ---")
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

    try:
        conn = get_db_connection()
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

def delete_admin():
    list_admins()
    username = input("Enter the username of the admin to delete (or press Enter to cancel): ").strip()
    if not username:
        return

    confirm = input(f"Are you sure you want to delete admin '{username}'? (y/N): ").lower()
    if confirm != 'y':
        print("Deletion cancelled.")
        return

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists and is an admin
        cursor.execute("SELECT * FROM users WHERE username = ? AND is_admin = 1", (username,))
        if not cursor.fetchone():
            print(f"Error: Admin user '{username}' not found.")
            conn.close()
            return

        cursor.execute("DELETE FROM users WHERE username = ? AND is_admin = 1", (username,))
        conn.commit()
        conn.close()
        print(f"Successfully deleted admin user: {username}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")

def main():
    while True:
        print("\n=== Admin Management Tool ===")
        print("1. List all admins")
        print("2. Create new admin")
        print("3. Delete an admin")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ")
        
        if choice == '1':
            list_admins()
        elif choice == '2':
            create_admin()
        elif choice == '3':
            delete_admin()
        elif choice == '4':
            print("Exiting.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
