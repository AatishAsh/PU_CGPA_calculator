import sqlite3
import os

DB_FILE = "database.db"

def run_manual_migration():
    if not os.path.exists(DB_FILE):
        print(f"Error: {DB_FILE} not found. Run app.py first.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("Checking for profile_pic column...")
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'profile_pic' not in columns:
        print("Adding profile_pic column...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN profile_pic TEXT DEFAULT 'default.png'")
            conn.commit()
            print("Successfully added profile_pic column.")
        except Exception as e:
            print(f"Error during ALTER TABLE: {e}")
    else:
        print("profile_pic column already exists.")
        
    conn.close()

if __name__ == "__main__":
    run_manual_migration()
