import sqlite3
import os

DB_FILE = "database.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            register_number TEXT,
            department TEXT DEFAULT 'CSE',
            cgpa REAL,
            is_admin BOOLEAN DEFAULT 0
        )
    ''')
    
    # Check for missing columns (for migrations)
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'department' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN department TEXT DEFAULT 'CSE'")
        
    if 'is_admin' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
    
    # Grades table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            semester TEXT,
            subject TEXT,
            grade TEXT,
            credit INTEGER,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')
    
    conn.commit()
    conn.close()
